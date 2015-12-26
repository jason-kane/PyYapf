# -*- coding: utf-8 -*-
"""
Sublime Text 3 Plugin to invoke Yapf on a python file.
"""
import codecs
import os
import re
import subprocess
import sys
import tempfile
import configparser

import sublime, sublime_plugin

KEY = "pyyapf"


def save_style_to_tempfile(style):
    # build config object
    cfg = configparser.RawConfigParser()
    cfg.add_section('style')
    for key, value in style.items():
        cfg.set('style', key, value)

    # dump it to temporary file
    fobj, fname = tempfile.mkstemp()
    cfg.write(os.fdopen(fobj, "w"))
    return fname


def is_python(view):
    return view.score_selector(0, 'source.python') > 0


class Yapf:
    """
    This class wraps YAPF invocation, including encoding/decoding and error handling.
    """

    def __init__(self, view):
        self.settings = sublime.load_settings("PyYapf.sublime-settings")
        self.view = view

    encoding = None
    debug = False

    def encode_selection(self, selection):
        try:
            encoded = self.view.substr(selection).encode(self.encoding)
        except UnicodeEncodeError as err:
            msg = "You may need to re-open this file with a different encoding. Current encoding is %r." % self.encoding
            self.error("UnicodeEncodeError: %s\n\n%s", err, msg)
            return

        self.indent = b""
        detected = False
        unindented = []
        for line in encoded.splitlines(keepends=True):
            if not detected:
                codeline = line.strip()
                if len(codeline) > 0:
                    self.indent, _, _ = line.partition(codeline)
                    detected = True
            unindented.append(line[len(self.indent):])
        unindented = b''.join(unindented)
        return unindented

    def replace_selection(self, edit, selection, output):
        indent = self.indent.decode(self.encoding)
        reindented = []
        for line in output.splitlines():
            reindented.append(indent + line + '\n')
        self.view.replace(edit, selection, ''.join(reindented))

    def format(self, selection, edit):
        """
        primary action when the plugin is triggered
        """
        print("Formatting selection with Yapf")

        self.encoding = self.view.encoding()

        if self.encoding == "Undefined":
            print('Encoding is not specified.')
            self.encoding = self.settings.get('default_encoding')

        print('Using encoding of %r' % self.encoding)

        self.debug = self.settings.get('debug')

        # encode selection
        encoded_selection = self.encode_selection(selection)
        if not encoded_selection:
            return

        # determine yapf command
        cmd = self.settings.get("yapf_command")
        assert cmd, "yapf_command not configured"
        cmd = os.path.expanduser(cmd)
        args = [cmd]

        # verify reformatted code
        args += ["--verify"]

        # override style?
        if self.settings.has('config'):
            custom_style = self.settings.get("config")
            style_filename = save_style_to_tempfile(custom_style)
            args += ["--style={0}".format(style_filename)]

            if self.debug:
                print('Using custom style:')
                with open(style_filename) as file_handle:
                    print(file_handle.read())
        else:
            style_filename = None

        # use directory of current file so that custom styles are found properly
        fname = self.view.file_name()
        cwd = os.path.dirname(fname) if fname else None

        # specify encoding in environment
        env = os.environ.copy()
        env['LANG'] = self.encoding

        # win32: hide console window
        if sys.platform in ('win32', 'cygwin'):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags = subprocess.CREATE_NEW_CONSOLE | subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        else:
            startupinfo = None

        # run yapf
        print('Running {0} in {1}'.format(args, cwd))
        if self.debug:
            print('Environment: {0}'.format(env))
        popen = subprocess.Popen(args,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 stdin=subprocess.PIPE,
                                 cwd=cwd,
                                 env=env,
                                 startupinfo=startupinfo)
        encoded_output, encoded_err = popen.communicate(encoded_selection)

        # handle errors (since yapf>=0.3, exit code 2 means changed, not error)
        if popen.returncode not in (0, 2):
            err = encoded_err.decode(self.encoding)
            print('Error:\n%s', err)

            # report error
            err_lines = err.splitlines()
            msg = err_lines[-1]
            if 'InternalError' in msg:
                sublime.error_message(msg)
            else:
                loc = err_lines[-4]
                loc = loc[loc.find('line'):].capitalize()
                sublime.error_message('%s (%s)' % (msg, loc))
        else:
            new_text = encoded_output.decode(self.encoding)
            self.replace_selection(edit, selection, new_text)

        if style_filename:
            os.unlink(style_filename)

        print('PyYapf Completed')


# pylint: disable=W0232
class YapfSelectionCommand(sublime_plugin.TextCommand):
    """
    The "yapf_selection" command formats the current selection (or the entire
    document if the "use_entire_file_if_no_selection" option is enabled).
    """

    def is_enabled(self):
        return is_python(self.view)

    def run(self, edit):
        yapf = Yapf(self.view)

        # there is always at least one region...
        for region in self.view.sel():
            # ...if it is empty then there is no selection
            if region.empty():
                if yapf.settings.get("use_entire_file_if_no_selection"):
                    selection = sublime.Region(0, self.view.size())
                else:
                    sublime.error_message('A selection is required')
                    break
            else:
                selection = region

            # format region
            yapf.format(selection, edit)


# pylint: disable=W0232
class YapfDocumentCommand(sublime_plugin.TextCommand):
    """
    The "yapf_document" command formats the current document.
    """

    def is_enabled(self):
        return is_python(self.view)

    def run(self, edit):
        selection = sublime.Region(0, self.view.size())
        Yapf(self.view).format(selection, edit)


class EventListener(sublime_plugin.EventListener):
    def on_pre_save(self, view):
        settings = sublime.load_settings("PyYapf.sublime-settings")
        if settings.get('on_save'):
            view.run_command('yapf_document')

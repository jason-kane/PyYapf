# -*- coding: utf-8 -*-
"""
Sublime Text 2/3 Plugin to invoke Yapf on a python file.
"""
try:
    from ConfigParser import RawConfigParser
except ImportError:
    from configparser import RawConfigParser

import codecs
import os
import re
import subprocess
import sys
import tempfile

import sublime, sublime_plugin

PY3 = (sys.version_info[0] >= 3)
KEY = "pyyapf"


def failure_parser(in_failure, encoding):
    """
    Parse the last line of a yapf traceback into something
    we can use (preferable row/column)
    """
    if isinstance(in_failure, UnicodeEncodeError):
        # so much easier when we have the actual exception
        err = in_failure.reason
        msg = in_failure.message

        msg = ("\nYou may need to re-open this file with a different"
               " encoding.  Current encoding is %r" % encoding)

        tval = {'context': "(\"\", %i)" % in_failure.start}
    else:
        # we got a string error from yapf
        #
        print('YAPF exception: %s' % in_failure)
        if PY3:
            in_failure = in_failure.decode()
        lastline = in_failure.strip().split('\n')[-1]
        err, msg = lastline.split(':')[0:2]
        detail = ":".join(lastline.strip().split(':')[2:])
        tval = {}
        stripped_comma = False
        key = None

        if err == "UnicodeEncodeError":
            # UnicodeEncodeError
            # 'ascii' codec can't encode characters in position 175337-175339
            # ordinal not in range(128)
            position = msg.split('-')[-1]
            tval = {'context': "(\"\", %i)" % int(position)}
        elif err == "UnicodeDecodeError":
            # UnicodeEncodeError
            # 'ascii' codec can't encode characters in position 130: ordinal
            # not in range(128)
            match = re.search(r'position (\d+)$', msg)
            if match:
                position = match.groups()[0]
                tval = {'context': "(\"\", %i)" % int(position)}
        else:
            for element in detail.split(' '):
                element = element.strip()
                if not element:
                    continue
                if "=" in element:
                    key, value = element.split('=')
                    stripped_comma = value[-1] == ","
                    value = value.rstrip(',')
                    tval[key] = value
                else:
                    if stripped_comma:
                        element = ", " + element
                    stripped_comma = False
                    tval[key] += element

    return err, msg, tval


def save_style_to_tempfile(in_dict):
    """
    Take a dictionary of yapf style settings and return the file
    name of a tempfile containing the expected config formatted
    style settings
    """

    cfg = RawConfigParser()
    cfg.add_section('style')
    for key in in_dict:
        cfg.set('style', key, in_dict[key])

    fobj, filename = tempfile.mkstemp()
    cfg.write(os.fdopen(fobj, "w"))
    return filename


# pylint: disable=W0232
class YapfCommand(sublime_plugin.TextCommand):
    """
    This is the actual class instantated by Sublime when
    the command 'yapf' is invoked.
    """
    view = None
    encoding = None
    debug = False

    def smart_failure(self, in_failure):
        """
        Take a failure exception or the stderr from yapf
        and try to extract useful information like what kind
        of problem is it and where in your code the problem is.
        """
        err, msg, context_dict = failure_parser(in_failure, self.encoding)

        sublime.error_message(
            "{0}\n{1}\n\n{2}".format(err, msg, repr(context_dict)))

        if 'context' in context_dict:
            #"('', (46,44))"
            rowcol = context_dict['context'][1:-1]

            # ignore the first arg
            rowcol = rowcol[rowcol.find(',') + 1:].strip()
            if rowcol[0] == "(":
                rowcol = rowcol[1:-1]  # remove parens
                row, col = rowcol.split(',')
                col = int(col)
                row = int(row)

                point = self.view.text_point(row - 1, col - 1)
                print('centering on row: %r, col: %r' % (row - 1, col - 1))
            else:
                point = int(rowcol)
                print('centering on character index %r' % point)

            # clear any existing pyyapf markers
            #pyyapf_regions = self.view.get_regions(KEY)
            self.view.erase_regions(KEY)

            scope = "pyyapf"
            region = self.view.line(point)
            self.view.add_regions(KEY, [region], scope, "dot")
            self.view.show_at_center(region)

            if self.debug:
                print(repr(in_failure))

    def encode_selection(self, selection):
        try:
            encoded = self.view.substr(selection).encode(self.encoding)
        except UnicodeEncodeError as err:
            self.smart_failure(err)
            return None

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
        reindented = []
        indent = self.indent.decode(self.encoding)
        line_endings = self.view.line_endings()
        for line in output.splitlines(keepends=True):
            reindented.append(indent + line)
        self.view.replace(edit, selection, ''.join(reindented))
        self.view.set_line_endings(line_endings)

    def run(self, edit):
        """
        primary action when the plugin is triggered
        """
        print("Formatting selection with Yapf")

        settings = sublime.load_settings("PyYapf.sublime-settings")

        self.encoding = self.view.encoding()

        if self.encoding == "Undefined":
            print('Encoding is not specified.')
            self.encoding = settings.get('default_encoding')

        print('Using encoding of %r' % self.encoding)

        self.debug = settings.get('debug')

        # there is always at least one region
        for region in self.view.sel():
            # determine selection to format
            if region.empty():
                if settings.get("use_entire_file_if_no_selection"):
                    selection = sublime.Region(0, self.view.size())
                else:
                    sublime.error_message('A selection is required')
                    continue
            else:
                selection = region

            # encode selection
            encoded_selection = self.encode_selection(selection)
            if not encoded_selection:
                continue

            # determine yapf command
            cmd = settings.get("yapf_command")
            assert cmd, "yapf_command not configured"
            cmd = os.path.expanduser(cmd)
            args = [cmd]

            # verify reformatted code
            args += ["--verify"]

            # override style?
            if settings.has('config'):
                custom_style = settings.get("config")
                style_filename = save_style_to_tempfile(custom_style)
                args += ["--style={0}".format(style_filename)]

                if self.debug:
                    print('Using custom style:')
                    with open(style_filename) as file_handle:
                        print(file_handle.read())
            else:
                style_filename = None

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
            print('Running {0}'.format(args))
            if self.debug:
                print('Environment: {0}'.format(env))
            popen = subprocess.Popen(args,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,
                                     stdin=subprocess.PIPE,
                                     env=env,
                                     startupinfo=startupinfo)
            output, output_err = popen.communicate(encoded_selection)

            # handle errors (since yapf>=0.3: exit code 2 means changed, not error)
            if popen.returncode not in (0, 2):
                try:
                    if not PY3:
                        output_err = output_err.encode(self.encoding)
                    self.smart_failure(output_err)

                # Catching too general exception
                # pylint: disable=W0703
                except Exception as err:
                    print('Unable to parse error: %r' % err)
                    if PY3:
                        output_err = output_err.decode()
                    sublime.error_message(output_err)
            else:
                output = output.decode(self.encoding)
                self.replace_selection(edit, selection, output)

            if style_filename:
                os.unlink(style_filename)

        # restore cursor
        print('restoring cursor to ', region, repr(region))
        self.view.show_at_center(region)

        print('PyYapf Completed')

    def is_enabled(self):
        is_python = self.view.score_selector(0, 'source.python') > 0
        return is_python

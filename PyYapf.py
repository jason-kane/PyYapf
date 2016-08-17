# -*- coding: utf-8 -*-
"""
Sublime Text 2-3 Plugin to invoke YAPF on a Python file.
"""
from __future__ import print_function
try:
    import configparser
except ImportError:
    import ConfigParser as configparser

import os
import subprocess
import sys
import tempfile
import textwrap

import sublime
import sublime_plugin

# make sure we don't choke on unicode when we reformat ourselves
u"我爱蟒蛇"

SUBLIME_3 = sys.version_info >= (3, 0)
KEY = "pyyapf"

if not SUBLIME_3:
    # backport from python 3.3 (https://hg.python.org/cpython/file/3.3/Lib/textwrap.py)
    def indent(text, prefix, predicate=None):
        """Adds 'prefix' to the beginning of selected lines in 'text'.
        If 'predicate' is provided, 'prefix' will only be added to the lines
        where 'predicate(line)' is True. If 'predicate' is not provided,
        it will default to adding 'prefix' to all non-empty lines that do not
        consist solely of whitespace characters.
        """

        if predicate is None:

            def predicate(line):
                return line.strip()

        def prefixed_lines():
            for line in text.splitlines(True):
                yield (prefix + line if predicate(line) else line)

        return ''.join(prefixed_lines())

    textwrap.indent = indent


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


def dedent_text(text):
    new_text = textwrap.dedent(text)
    if not new_text:
        return new_text, '', False

    # determine original indentation
    old_first = text.splitlines()[0]
    new_first = new_text.splitlines()[0]
    assert old_first.endswith(new_first), 'PyYapf: Dedent logic flawed'
    indent = old_first[:len(old_first) - len(new_first)]

    # determine if have trailing newline (when using the "yapf_selection"
    # command, it can happen that there is none)
    trailing_nl = text.endswith('\n')

    return new_text, indent, trailing_nl


def indent_text(text, indent, trailing_nl):
    # reindent
    text = textwrap.indent(text, indent)

    # remove trailing newline if so desired
    if not trailing_nl and text.endswith('\n'):
        text = text[:-1]

    return text


def parse_error_line(err_lines):
    """
    Parse YAPF output to determine line on which error occurred.
    """
    msg = err_lines[-1]

    # yapf.yapflib.verifier.InternalError: Missing parentheses in call to 'print' (<string>, line 2)
    if '(<string>, line ' in msg:
        return int(msg.rstrip(')').rsplit(None, 1)[1]) + 1

    # lib2to3.pgen2.tokenize.TokenError: ('EOF in multi-line statement', (5, 0))
    if msg.endswith('))'):
        return int(msg.rstrip(')').rsplit(None, 2)[1].strip(',('))

    #   File "<unknown>", line 3
    #     if:
    #       ^
    # SyntaxError: invalid syntax
    if len(err_lines) >= 4 and ', line' in err_lines[-4]:
        return int(err_lines[-4].rsplit(None, 1)[1])


if SUBLIME_3:
    ERROR_FLAGS = sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE | sublime.DRAW_SQUIGGLY_UNDERLINE
else:
    ERROR_FLAGS = sublime.DRAW_OUTLINED


class Yapf:
    """
    This class wraps YAPF invocation, including encoding/decoding and error handling.
    """

    def __init__(self, view):
        self.view = view

    def __enter__(self):
        self.settings = sublime.load_settings("PyYapf.sublime-settings")

        # determine encoding
        self.encoding = self.view.encoding()
        if self.encoding in ['Undefined', None]:
            self.encoding = self.settings.get('default_encoding')
            self.debug('Encoding is not specified, falling back to default %r',
                       self.encoding)
        else:
            self.debug('Encoding is %r', self.encoding)

        # custom style options?
        custom_style = self.settings.get("config")
        if custom_style:
            # write style file to temporary file
            self.custom_style_fname = save_style_to_tempfile(custom_style)
            self.debug('Using custom style (%s):\n%s', self.custom_style_fname,
                       open(self.custom_style_fname).read().strip())
        else:
            self.custom_style_fname = None

        # prepare popen arguments
        cmd = self.settings.get("yapf_command")
        if not cmd:
            # always show error in popup
            msg = 'Yapf command not configured. Problem with settings?'
            sublime.error_message(msg)
            raise Exception(msg)
        cmd = os.path.expanduser(cmd)

        self.popen_args = [cmd]
        if self.custom_style_fname:
            self.popen_args += ['--style', self.custom_style_fname]

        # use directory of current file so that custom styles are found properly
        fname = self.view.file_name()
        self.popen_cwd = os.path.dirname(fname) if fname else None

        # specify encoding in environment
        self.popen_env = os.environ.copy()
        self.popen_env['LANG'] = self.encoding

        # win32: hide console window
        if sys.platform in ('win32', 'cygwin'):
            self.popen_startupinfo = subprocess.STARTUPINFO()
            self.popen_startupinfo.dwFlags = subprocess.CREATE_NEW_CONSOLE | subprocess.STARTF_USESHOWWINDOW
            self.popen_startupinfo.wShowWindow = subprocess.SW_HIDE
        else:
            self.popen_startupinfo = None

        # clear marked regions and status
        self.view.erase_regions(KEY)
        self.view.erase_status(KEY)
        self.errors = []
        return self

    def __exit__(self, type, value, traceback):
        if self.custom_style_fname:
            os.unlink(self.custom_style_fname)

    def format(self, edit, selection=None):
        """
        Format selection (if None then formats the entire document).
        Returns region containing the reformatted text.
        """
        # determine selection to format
        if not selection:
            selection = sublime.Region(0, self.view.size())
        self.debug('Formatting selection %r', selection)

        # retrieve selected text & dedent
        text = self.view.substr(selection)
        text, indent, trailing_nl = dedent_text(text)
        self.debug('Detected indent %r', indent)

        # encode text
        try:
            encoded_text = text.encode(self.encoding)
        except UnicodeEncodeError as err:
            msg = "You may need to re-open this file with a different encoding. Current encoding is %r." % self.encoding
            self.error("UnicodeEncodeError: %s\n\n%s", err, msg)
            return

        # pass source code to be formatted on stdin?
        if self.settings.get("use_stdin"):
            # run yapf
            self.debug('Running %s in %s', self.popen_args, self.popen_cwd)
            try:
                popen = subprocess.Popen(self.popen_args,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE,
                                         stdin=subprocess.PIPE,
                                         cwd=self.popen_cwd,
                                         env=self.popen_env,
                                         startupinfo=self.popen_startupinfo)
            except OSError as err:
                # always show error in popup
                msg = "You may need to install YAPF and/or configure 'yapf_command' in PyYapf's Settings."
                sublime.error_message("OSError: %s\n\n%s" % (err, msg))
                return
            encoded_stdout, encoded_stderr = popen.communicate(encoded_text)
            text = encoded_stdout.decode(self.encoding)
        else:
            # do _not_ use stdin.  this avoids a unicode defect in yapf, see
            # https://github.com/google/yapf/pull/145.  once yapf is fixed
            # we may remove the use_stdin option and this code.
            file_obj, temp_filename = tempfile.mkstemp(suffix=".py")
            try:
                temp_handle = os.fdopen(file_obj, 'wb' if SUBLIME_3 else 'w')
                temp_handle.write(encoded_text)
                temp_handle.close()
                self.popen_args += ["--in-place", temp_filename]

                self.debug('Running %s in %s', self.popen_args, self.popen_cwd)
                try:
                    popen = subprocess.Popen(
                        self.popen_args,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        cwd=self.popen_cwd,
                        env=self.popen_env,
                        startupinfo=self.popen_startupinfo)
                except OSError as err:
                    # always show error in popup
                    msg = "You may need to install YAPF and/or configure 'yapf_command' in PyYapf's Settings."
                    sublime.error_message("OSError: %s\n\n%s" % (err, msg))
                    return

                encoded_stdout, encoded_stderr = popen.communicate()

                if SUBLIME_3:
                    open_encoded = open
                else:
                    import codecs
                    open_encoded = codecs.open

                with open_encoded(temp_filename, encoding=self.encoding) as fp:
                    text = fp.read()
            finally:
                os.unlink(temp_filename)

        self.debug('Exit code %d', popen.returncode)

        # handle errors (since yapf>=0.3, exit code 2 means changed, not error)
        if popen.returncode not in (0, 2):
            stderr = encoded_stderr.decode(self.encoding)
            stderr = stderr.replace(os.linesep, '\n')
            self.debug('Error:\n%s', stderr)

            # report error
            err_lines = stderr.splitlines()
            msg = err_lines[-1]
            self.error('%s', msg)

            # attempt to highlight line where error occurred
            rel_line = parse_error_line(err_lines)
            if rel_line:
                line = self.view.rowcol(selection.begin())[0]
                pt = self.view.text_point(line + rel_line - 1, 0)
                region = self.view.line(pt)
                self.view.add_regions(KEY, [region], KEY, 'cross', ERROR_FLAGS)
            return

        # adjust newlines (only necessary when use_stdin is True, since
        # [codecs.]open uses universal newlines by default)
        text = text.replace(os.linesep, '\n')

        # re-indent and replace text
        text = indent_text(text, indent, trailing_nl)
        self.view.replace(edit, selection, text)

        # return region containing modified text
        if selection.a <= selection.b:
            return sublime.Region(selection.a, selection.a + len(text))
        else:
            return sublime.Region(selection.b + len(text), selection.b)

    def debug(self, msg, *args):
        if self.settings.get('debug'):
            print('PyYapf:', msg % args)

    def error(self, msg, *args):
        msg = msg % args

        # add to status bar
        self.errors.append(msg)
        self.view.set_status(KEY, 'PyYapf: %s' % ', '.join(self.errors))
        if self.settings.get('popup_errors'):
            sublime.error_message(msg)


def is_python(view):
    return view.score_selector(0, 'source.python') > 0


if not SUBLIME_3:

    class PreserveSelectionAndView:
        """
        This context manager assists in preserving the selection and view
        when text is replaced.
        """

        def __init__(self, view):
            self.view = view

        def __enter__(self):
            # save selection and view
            self.sel = list(self.view.sel())
            self.visible_region_begin = self.view.visible_region().begin()
            self.viewport_position = self.view.viewport_position()
            return self

        def __exit__(self, type, value, traceback):
            # restore selection
            self.view.sel().clear()
            for s in self.sel:
                self.view.sel().add(s)

            # restore view (this is somewhat cargo cultish, not sure why a single statement does not suffice)
            self.view.show(self.visible_region_begin)
            self.view.set_viewport_position(self.viewport_position)
else:

    class PreserveSelectionAndView:
        """
        This context manager assists in preserving the selection when text is replaced.
        (Sublime Text 3 already does a good job preserving the view.)
        """

        def __init__(self, view):
            self.view = view

        def __enter__(self):
            # save selection
            self.sel = list(self.view.sel())
            return self

        def __exit__(self, type, value, traceback):
            # restore selection
            self.view.sel().clear()
            for s in self.sel:
                self.view.sel().add(s)


class YapfSelectionCommand(sublime_plugin.TextCommand):
    """
    The "yapf_selection" command formats the current selection (or the entire
    document if the "use_entire_file_if_no_selection" option is enabled).
    """

    def is_enabled(self):
        return is_python(self.view)

    def run(self, edit):
        with Yapf(self.view) as yapf:
            # no selection?
            no_selection = all(s.empty() for s in self.view.sel())
            if no_selection:
                if not yapf.settings.get("use_entire_file_if_no_selection"):
                    sublime.error_message('A selection is required')
                    return

                # format entire document
                with PreserveSelectionAndView(self.view):
                    yapf.format(edit)
                return

            # otherwise format all (non-empty) ones
            with PreserveSelectionAndView(self.view) as pv:
                pv.sel = []
                for s in self.view.sel():
                    if not s.empty():
                        new_s = yapf.format(edit, s)
                        pv.sel.append(new_s if new_s else s)


class YapfDocumentCommand(sublime_plugin.TextCommand):
    """
    The "yapf_document" command formats the current document.
    """

    def is_enabled(self):
        return is_python(self.view)

    def run(self, edit):
        with PreserveSelectionAndView(self.view):
            with Yapf(self.view) as yapf:
                yapf.format(edit)


class EventListener(sublime_plugin.EventListener):
    def on_pre_save(self, view):  # pylint: disable=no-self-use
        settings = sublime.load_settings("PyYapf.sublime-settings")
        if settings.get('on_save'):
            view.run_command('yapf_document')

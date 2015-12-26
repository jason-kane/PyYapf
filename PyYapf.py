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

    def save_selection_to_tempfile(self, selection):
        """
        dump the current selection to a tempfile
        and return the filename.  caller is responsible
        for cleanup.
        """
        fobj, filename = tempfile.mkstemp(suffix=".py")
        temphandle = os.fdopen(fobj, 'wb' if PY3 else 'w')

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

        temphandle.write(b''.join(unindented))
        temphandle.close()
        return filename

    def replace_selection(self, edit, selection, output):
        reindented = []
        indent = self.indent.decode(self.encoding)
        for line in output.splitlines(keepends=True):
            reindented.append(indent + line)
        self.view.replace(edit, selection, ''.join(reindented))

    def run(self, edit):
        """
        primary action when the plugin is triggered
        """
        print("Formatting selection with Yapf")

        settings = sublime.load_settings("PyYapf.sublime-settings")

        self.encoding = self.view.encoding()

        if self.encoding == "Undefined":
            print('Encoding is not specified.')
            self.encoding = settings.get('default_encoding', 'UTF-8')

        print('Using encoding of %r' % self.encoding)

        self.debug = settings.get('debug', False)

        # there is always at least one region
        for region in self.view.sel():
            if region.empty():
                if settings.get("use_entire_file_if_no_selection", True):
                    selection = sublime.Region(0, self.view.size())
                else:
                    sublime.error_message('A selection is required')
                    selection = None
            else:
                selection = region

            if selection:
                py_filename = self.save_selection_to_tempfile(selection)

                if py_filename:
                    style_filename = save_style_to_tempfile(
                        settings.get("config", {}))

                    yapf = os.path.expanduser(
                        settings.get("yapf_command", "/usr/local/bin/yapf"))

                    cmd = [yapf, "--style={0}".format(style_filename),
                           "--verify", "--in-place", py_filename]

                    print('Running {0}'.format(cmd))
                    environment = os.environ.copy()
                    environment['LANG'] = self.encoding
                    proc = subprocess.Popen(cmd,
                                            stderr=subprocess.PIPE,
                                            env=environment)

                    output, output_err = proc.communicate()

                    temphandle = codecs.open(py_filename,
                                             encoding=self.encoding)
                    output = temphandle.read()
                    temphandle.close()

                    if not output_err:
                        self.replace_selection(edit, selection, output)
                    else:
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

                    if self.debug:
                        with open(style_filename) as file_handle:
                            print(file_handle.read())

                    os.unlink(py_filename)
                os.unlink(style_filename)

        print('restoring cursor to ', region, repr(region))
        self.view.show_at_center(region)

        print('PyYapf Completed')

    def is_enabled(self):
        is_python = self.view.score_selector(0, 'source.python') > 0
        return is_python

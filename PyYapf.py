"""
Sublime Text 2 Plugin to invoke Yapf on a python file.
"""

import ConfigParser
import os
import subprocess
import tempfile

import sublime, sublime_plugin


class YapfCommand(sublime_plugin.TextCommand):
    def make_style(self, in_dict):
        """
        Take a dictionary of yapf style settings and return the file
        name of a tempfile containing the expected config formatted
        style settings
        """

        cfg = ConfigParser.RawConfigParser()
        cfg.add_section('style')
        for key in in_dict:
            cfg.set('style', key, in_dict[key])

        fobj, fn = tempfile.mkstemp()
        cfg.write(os.fdopen(fobj, "w"))
        return fn

    def run(self, edit):
        """
        primary action when the plugin is triggered
        """
        print("Formatting selection with Yapf")

        settings = sublime.load_settings("PyYapf.sublime-settings")

        for region in self.view.sel():
            if region.empty() and settings.get(
                "use_entire_file_if_no_selection", True):
                selection = sublime.Region(0, self.view.size())
            else:
                selection = region

            style = self.make_style(settings.get("config", {}))
            cmd = ['/usr/local/bin/yapf', "--style={0}".format(style),
                   "--verify"]

            print('Running {0}'.format(cmd))
            proc = subprocess.Popen(cmd,
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            output, output_err = proc.communicate(self.view.substr(selection))

            if output_err == "":
                self.view.replace(edit, selection, output)
            else:
                sublime.error_message(output_err)

        print('PyYapf Completed')

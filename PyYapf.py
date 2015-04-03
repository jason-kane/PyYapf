import sublime, sublime_plugin
from yapf import yapf_api
from yapf.yapflib import style

s = sublime.load_settings("PyYapf.sublime-settings")


class YapfCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        mystyle = style.CreatePEP8Style()
        mystyle.update(s.get("config", {}))

        style.SetGlobalStyle(mystyle)

        for region in self.view.sel():

            selected_entire_file = False

            if region.empty() and s.get("use_entire_file_if_no_selection",
                                        True):
                selection = sublime.Region(0, self.view.size())
                selected_entire_file = True
            else:
                selection = region

            self.view.replace(edit, selection,
                              yapf_api.FormatCode(self.view.substr(selection)))

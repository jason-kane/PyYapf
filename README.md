# PyYapf

Sublime Text 3 plugin to run the [YAPF](https://github.com/google/yapf) Python formatter

## Usage

By default, press `Ctrl-Alt-F` to format the current selection (or the entire document if nothing is selected).
You can also `Ctrl-Shift-P` (Mac: `Cmd-Shift-P`) and select "PyYapf: Format Selection" or "PyYapf: Format Document".
To automatically run YAPF on the current document before saving, use the `on_save` setting.

##Installation

1.  Install YAPF (if you haven't already):
   ```
   pip install yapf
   ```

2.  Install Sublime Package Control by following the instructions [here](https://packagecontrol.io/installation) (if you haven't already).

3.  `Ctrl-Shift-P` (Mac: `Cmd-Shift-P`) and choose "Package Control: Install Package".

4.  Find PyYapf in the list (type in a few characters and you should see it).

##Problems?

This makes it pretty easy to find valid python code that makes Yapf choke or give bad formatting.
Please try to reduce any problems to a minimal example and [let the YAPF folks know](https://github.com/google/yapf/issues).
If there is something wrong with this plugin, [add an issue](https://github.com/jason-kane/PyYapf/issues) on GitHub and I'll try to address it.

##LICENSE

Apache v2 per LICENSE.  Do what you want; if you fix something please share it.

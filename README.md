# PyYapf

Sublime 2/3 plugin to run the [YAPF](https://github.com/google/yapf) Python formatter

## Usage

By default, press `Ctrl-Alt-F` to format the current selection (or the entire document if nothing is selected).
You can also `Ctrl-Shift-P` and select "PyYapf: Format Selection".

##Installation

1.  Install yapf (if you haven't already)
   ```
   pip install yapf
   ```

2.  Install Sublime Package Control (if you haven't already)
    Instructions can be found at:
   ```
   https://packagecontrol.io/installation
   ```

3.  Control-Shift-P (mac: command-shift-p), Choose "Package Control: Install Package"

4.  Find PyYapf in the list (type in a few characters and you should see it)

##Problems?

This makes it pretty easy to find valid python code that makes Yapf choke or give bad formatting.  Please try to reduce any problems to a minimal example and let the Yapf folks know.  If there is something wrong with this plugin add an Issue on GitHub and I'll try to address it.

##LICENSE

Apache v2 per LICENSE.  Do what you want; if you fix something please share it.

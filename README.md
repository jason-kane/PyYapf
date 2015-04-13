# PyYapf
Sublime 2/3 plugin to run Yapf Python formatter

https://github.com/google/yapf

I have PyYapf bound by default to ctrl-alt-f.  You can also ctrl-shift-p then "PyYapf: Reformat Python".

##Installation

1.  Install yapf
   ```
   pip install yapf
   ```

2.  Install Sublime Package Control
   ```
   https://packagecontrol.io/installation
   ```

3.  Control-Shift-P, "Package Control: Install Package"
4.  Find PyYapf in the list (type in a few characters and you'll seee it)


##Problems?

This makes it pretty easy to find valid python code that makes Yapf choke.  Please try to reduce the problem to a minimal example and let the Yapf folks know.  If there is something wrong with this plugin add an Issue on GitHub and I'll probably fix it.

##LICENSE

YAPF is Apache v2 licenced, the lib2to3 from 2.7 is PSF v2; as far as I can tell the PSF is fine as long as I include the license.  Ditto with YAPF.  If I'm wrong let me know and I'll fix it.  For my part Apache v2 applies.  Do what you want; if you fix something please share it.

# PyYapf
Sublime 2 plugin to run Yapf Python formatter

Ok campers, gather round.

This is a Sublime Text 2 plugin for YAPF

https://github.com/google/yapf

Now for the "fun".. Yapf doesn't support the Python 2.6 that is baked into Sublime-Text 2.  So I backported it.  In doing so I broke the command line capabilities and who knows what else.

Yapf makes heavy use of lib2to3.  Sublime doesn't ship with lib2to3 at all and the version of lib2to3 that comes with Python 2.6 doesn't provide the capabilities that Yapf expects.  So I snagged the lib2to3 from 2.7 and crossed my fingers.

For some inexplicable reason the end result actually seems to work.  I have it bound by default to ctrl-alt-f.  You can also ctrl-shift-p then "PyYapf: Reformat Python".

##Installation

Once this has more than a half dozen runs under it's tires I'll add it to Package Control for easy-to-install goodness.

Until then something like this should get it going:

```sh
git clone https://github.com/jason-kane/PyYapf.git
cp -R SublimePyYapf ~/.config/sublime-text2/Packages/
```

##Sublime 2 Only!

Once I get around to upgrading to Sublime 3 I'll either update this plugin or make a new one.  As much as I hacked on things I doubt it will work in Sublime 3 without help.

##LICENSE

YAPF is Apache v2 licenced, the lib2to3 from 2.7 is PSF v2; as far as I can tell the PSF is fine as long as I include the license.  Ditto with YAPF.  If I'm wrong let me know and I'll fix it.  For my part Apache v2 applies.  Do what you want; if you fix something please share it.

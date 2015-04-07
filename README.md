# PyYapf
Sublime 2 plugin to run Yapf Python formatter

Ok campers, gather round.

This is a Sublime Text 2 plugin for Yapf

https://github.com/google/yapf

You will need to install yapf first.  When I installed it:
*  I did a clone of the yapf git
*  changed dist.utils to setuptools in the setup.py
*  ran sudo python ./setup.py install

yapf is very much in active flux so I expect they will make it pip install-able soon.

I have PyYapf bound by default to ctrl-alt-f.  You can also ctrl-shift-p then "PyYapf: Reformat Python".

##Installation

1.  First install yapf.
```
pip install yapf
```

2.  Install the PyYapf sublime-text plugin.
I've submitted PyYapf to Package Control.  We should have simple installs soon.

Until then something like this should get it going (where ~/.config/sublime-text2/Packages/ is your sublime-text package directory):

```sh
cd ~/.config/sublime-text2/Packages/
git clone https://github.com/jason-kane/PyYapf.git
```

##Problems?

This makes it pretty easy to find valid python code that makes Yapf choke.  Please try to reduce the problem to a minimal example and let the Yapf folks know.  If there is something wrong with this plugin add an Issue on GitHub and I'll probably fix it.


##Sublime 2 Only (probably)

Once I get around to upgrading to Sublime 3 I'll update this plugin to work with both.

##LICENSE

YAPF is Apache v2 licenced, the lib2to3 from 2.7 is PSF v2; as far as I can tell the PSF is fine as long as I include the license.  Ditto with YAPF.  If I'm wrong let me know and I'll fix it.  For my part Apache v2 applies.  Do what you want; if you fix something please share it.

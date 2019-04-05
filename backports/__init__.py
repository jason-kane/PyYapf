# from https://github.com/minrk/backports.shutil_which

from pkgutil import extend_path
__path__ = extend_path(__path__, __name__)
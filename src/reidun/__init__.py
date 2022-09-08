import importlib.metadata
from pathlib import Path

from appdirs import AppDirs

__version__ = importlib.metadata.version("reidun")
_APP_DIRS = AppDirs("net.nausicaea.reidun", "nausicaea")
_CACHE_DIR = Path(_APP_DIRS.user_cache_dir)

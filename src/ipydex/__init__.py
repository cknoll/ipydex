try:
    from .core import *
except ImportError:
    pass
from .release import __version__

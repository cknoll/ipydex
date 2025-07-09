try:
    from .core import *
    from .utils import get_file_name_of_caller
except ImportError:
    pass
from .release import __version__

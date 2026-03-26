from pathlib import Path
_uavdex_root = Path(__file__).parent

from uavdex.common import *
from uavdex.propulsions import *
from uavdex.utils import *

try:
    from importlib.metadata import version, PackageNotFoundError
except ImportError:  # For Python < 3.8
    from importlib_metadata import version, PackageNotFoundError

try:
    __version__ = version("uavdex")
except PackageNotFoundError:
    __version__ = "unknown"

import pkg_resources

from .client import QuetzClient

try:
    __version__ = pkg_resources.get_distribution(__name__).version
except Exception:
    __version__ = "unknown"

__all__ = ("QuetzClient",)

"""Compatibility shim.

The implementation lives in `app.utils.logger`.
"""

from .utils.logger import configure_logging, get_logger

__all__ = ["configure_logging", "get_logger"]

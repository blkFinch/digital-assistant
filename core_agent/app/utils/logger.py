import logging
import sys

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds color to log levels."""

    COLORS = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT,
    }

    def format(self, record: logging.LogRecord) -> str:
        if COLORAMA_AVAILABLE:
            levelname = record.levelname
            color = self.COLORS.get(record.levelno, Fore.WHITE)
            record.levelname = f"{color}{levelname}{Style.RESET_ALL}"
        return super().format(record)


def configure_logging(debug: bool = False) -> None:
    """Configure root logging for the CLI run with optional colors."""
    level = logging.DEBUG if debug else logging.WARNING
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add new handler with colored formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    if COLORAMA_AVAILABLE:
        formatter = ColoredFormatter(LOG_FORMAT)
    else:
        formatter = logging.Formatter(LOG_FORMAT)

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger."""
    return logging.getLogger(name)
import io
import logging
import os
import sys

import coloredlogs


def _get_utf8_stream():
    """Return a UTF-8 capable stream for console logging on Windows."""
    stream = sys.stdout
    encoding = (getattr(stream, "encoding", "") or "").lower()
    if encoding == "utf-8":
        return stream

    # Wrap stdout with UTF-8 to avoid UnicodeEncodeError on cp1252 consoles.
    if hasattr(stream, "buffer"):
        return io.TextIOWrapper(stream.buffer, encoding="utf-8", errors="replace", write_through=True)
    return stream

def setup_logging(logs):
    if not os.path.exists("logs"):
        os.makedirs("logs")

    # Set up the logger
    logger = logging.getLogger(logs)
    logger.setLevel(logging.INFO)

    # Avoid adding duplicate handlers when setup_logging is called repeatedly.
    if logger.handlers:
        return logger

    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    coloredlogs.install(level='INFO', fmt=log_format, logger=logger, stream=_get_utf8_stream())
    file_handler = logging.FileHandler('logs/logs.log', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(file_handler)
    
    return logger
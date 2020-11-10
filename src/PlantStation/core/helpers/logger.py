import logging
from pathlib import Path
from typing import Optional


def get_root_logger(debug: bool = False, filename: Optional[Path] = None) -> logging.Logger:
    """Configures root logger

    Args:
        debug (bool): debug mode
        filename (Optional[Path]): optional filename where log should be saved

    Returns:
        (logging.Logger) root logger

        """
    logger = logging.getLogger()

    Formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    channel = logging.StreamHandler()
    channel.setFormatter(Formatter)
    logger.addHandler(channel)

    if filename:
        logfile = logging.FileHandler(filename)
        logfile.setFormatter(Formatter)
        logger.addHandler(logfile)

    logger.setLevel(logging.DEBUG if debug else logging.INFO)

    return logger

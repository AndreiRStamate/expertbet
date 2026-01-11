import logging
import sys

def setup_logging():
    """
    Configures logging to stdout for Fly deployments.
    """
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    logger = logging.getLogger(__name__)
    return logger
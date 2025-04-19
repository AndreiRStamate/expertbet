import logging

def setup_logging(log_file='log_file.log'):
    """
    Configures the logging system to write logs to a file and format them.
    """
    logging.basicConfig(
        filename=log_file,
        filemode='a',
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    return logger
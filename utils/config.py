import json
import logging

logger = logging.getLogger(__name__)

def load_config(config_file):
    """
    Loads the configuration from a JSON file.
    """
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        logger.info("Configuration loaded from %s", config_file)
        return config
    except FileNotFoundError:
        logger.error("Configuration file not found: %s", config_file)
        return {}
    except json.JSONDecodeError as e:
        logger.error("Error decoding JSON from configuration file %s: %s", config_file, e)
        return {}
    except Exception as e:
        logger.error("Error loading configuration from %s: %s", config_file, e)
        return {}
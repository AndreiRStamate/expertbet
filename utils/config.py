import json
import logging
import requests
from constants import CONFIG_FILE

logger = logging.getLogger(__name__)

def build_config_from_api(api_key: str):
    """
    Fetch leagues from the Odds API and generate a config.json file
    containing only football and basketball leagues.
    """
    url = f"https://api.the-odds-api.com/v4/sports?apiKey={api_key}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        leagues = response.json()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch leagues from API: {e}")
        return False

    config = {
        "football": [league["key"] for league in leagues if league.get("group") == "Soccer" and league.get("active", False)],
        "basketball": [league["key"] for league in leagues if league.get("group") == "Basketball" and league.get("active", False)],
        "default_days": 1,
        "number_of_matches": -1
    }

    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        logger.info(f"Config file created at {CONFIG_FILE}")
        return True
    except IOError as e:
        logger.error(f"Failed to write config file: {e}")
        return False

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
import os
import json
import datetime
import logging
from constants import CACHE_FOLDER
from utils.api import fetch_api_response

logger = logging.getLogger(__name__)

def get_cached_api_response(league):
    """
    Retrieves cached API response for a specific league if the cache is valid.
    Cache is considered valid if the last modification date matches today's date.
    """

    sport_folder = get_sport_folder(league)
    if not sport_folder:
        return None

    cache_folder = os.path.join(CACHE_FOLDER, sport_folder)
    os.makedirs(cache_folder, exist_ok=True)  # Ensure the sport-specific folder exists

    cache_file = os.path.join(cache_folder, f"api_response_{league}.json")
    if os.path.exists(cache_file):
        try:
            mod_time = datetime.date.fromtimestamp(os.path.getmtime(cache_file))
            today = datetime.date.today()
            if mod_time == today:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                logger.info("Cache hit for league %s: %s", league, cache_file)
                return data
            else:
                logger.info("Cache expired for league %s: %s", league, cache_file)
        except Exception as e:
            logger.error("Error reading cache file %s: %s", cache_file, e)
    else:
        logger.info("No cache found for league %s", league)
    return None

def save_to_cache(league, data, cache_folder):
    """
    Saves API response data to the cache for a specific league.
    """
    cache_file = os.path.join(cache_folder, f"api_response_{league}.json")
    try:
        os.makedirs(cache_folder, exist_ok=True)  # Ensure the cache folder exists
        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("Data cached for league %s: %s", league, cache_file)
    except Exception as e:
        logger.error("Error saving data to cache for league %s: %s", league, e)

def load_json(file_path):
    """
    Loads JSON data from a file. Returns an empty list if the file doesn't exist.
    """
    try:
        with open(file_path, "r") as file:
            logging.debug("Loading JSON data from %s", file_path)
            return json.load(file)
    except FileNotFoundError:
        logger.warning("File not found: %s", file_path)
        return []
    except Exception as e:
        logger.error("Error reading JSON file %s: %s", file_path, e)
        return []

def merge_json(old_data, new_data):
    """
    Merges two JSON datasets. Entries in new_data overwrite those in old_data if IDs match.
    """
    merged_data = {entry["id"]: entry for entry in old_data}  # Use old data as base
    if new_data:
        for entry in new_data:
            merged_data[entry["id"]] = entry  # Overwrite or add new data
    logger.debug("Merged JSON data: %s", merged_data)
    return list(merged_data.values())

def get_sport_folder(league):
    """
    Determines the sport folder based on the league name.
    """
    if "soccer" in league: # so stupid. . .
        return "football"
    elif "basketball" in league:
        return "basketball"
    elif "icehockey" in league:
        return "hockey"
    elif "cricket" in league:
        return "cricket"
    else:
        logger.error("Unknown sport for league %s", league)
        return None

def fetch_api_response_with_cache(league):
    """
    Fetches API response for a league, using cache if available.
    """
    api_key = os.getenv("THE_ODDS_API_KEY")
    if not api_key:
        logger.error("API key is missing. Set THE_ODDS_API_KEY in your environment.")
        return None

    # Determine the sport folder based on the league
    sport_folder = get_sport_folder(league)
    if not sport_folder:
        return None

    cache_folder = os.path.join(CACHE_FOLDER, sport_folder)
    os.makedirs(cache_folder, exist_ok=True)  # Ensure the sport-specific folder exists

    # Check cache first
    cached_data = get_cached_api_response(league)
    if cached_data:
        return cached_data

    cache_file = os.path.join(cache_folder, f"api_response_{league}.json")
    # Load existing cache data
    old_data = load_json(cache_file)

    # Fetch new data from the API
    new_data = fetch_api_response(league, api_key)

    merged_data = merge_json(old_data, new_data) if old_data else new_data

    # Save the new data to cache
    save_to_cache(league, merged_data, cache_folder)
    return new_data
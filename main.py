# Released under the MIT-0 License. Do whatever you want. No warranty.

import os
from dotenv import load_dotenv
import argparse
from constants import *
from utils.logging_config import setup_logging
from utils.match_processing import compute_predictability, get_matches_sorted, decide_action, print_match
from utils.file_operations import create_tip_file
from utils.cache import fetch_api_response_with_cache, get_cached_api_response
from utils.config import load_config
import json
import requests

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

logger = setup_logging()
load_dotenv(override=True)

def main():
    # Ensure the cache folder exists
    os.makedirs(CACHE_FOLDER, exist_ok=True)

    parser = argparse.ArgumentParser(description="Predict matches for various sports.")
    parser.add_argument("--football", action="store_true", help="Parse only football leagues.")
    parser.add_argument("--basketball", action="store_true", help="Parse only basketball leagues.")
    parser.add_argument("--hockey", action="store_true", help="Parse only hockey leagues.")
    parser.add_argument("--days", type=int, default=None, help="Number of days to fetch matches for.")
    args = parser.parse_args()

    build_config_from_api(os.getenv("THE_ODDS_API_KEY"))
    config = load_config(CONFIG_FILE)

    # Determine which leagues to parse
    actualSport  = "football"
    if sum([args.football, args.basketball, args.hockey]) > 1:
        logger.error("Cannot specify multiple sports at the same time.")
        return
    elif args.football:
        leagues = config.get("football", [])
    elif args.basketball:
        leagues = config.get("basketball", [])
        actualSport = "basketball"
    elif args.hockey:
        leagues = config.get("hockey", [])
        actualSport = "hockey"
    else:
        leagues = config.get("football", []) + config.get("basketball", []) + config.get("hockey", [])

    nr_zile = args.days if args.days is not None else config.get("default_days", 1)
    number_of_matches = config.get("number_of_matches", 5)

    predictable_matches = get_matches_sorted(
        by="predictability",
        nr_zile=nr_zile,
        top_n=number_of_matches,
        leagues=leagues,
        get_api_data=fetch_api_response_with_cache,
        get_cached_data=get_cached_api_response
    )
    if not predictable_matches:
        logger.info("No matches found for the specified interval or data is unavailable.")
        return

    sorted_matches = get_matches_sorted(
        by="commence_time",
        nr_zile=nr_zile,
        top_n=number_of_matches,
        leagues=leagues,
        get_api_data=fetch_api_response_with_cache,
        get_cached_data=get_cached_api_response
    )
    if not sorted_matches:
        logger.info("No matches found for the specified interval or data is unavailable.")
        return

    with open(OUTPUT_FILE, "a") as f:
        f.write(f"Matches in the next {nr_zile} days from leagues: {', '.join(leagues)}\n")
        f.write("Sorted by confidence level:\n")
    for match in predictable_matches:
        action = decide_action(match, threshold=1.0)
        print_match(match, action, OUTPUT_FILE)
        create_tip_file(match, action, actualSport)

    with open(OUTPUT_FILE, "a") as f:
        f.write("\nSorted by time of play:\n")
    for match in sorted_matches:
        action = decide_action(match, threshold=1.0)
        print_match(match, action, OUTPUT_FILE)

if __name__ == '__main__':
    main()

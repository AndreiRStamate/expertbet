# Released under the MIT-0 License. Do whatever you want. No warranty.

import os
from dotenv import load_dotenv
import argparse
from constants import *
from utils.logging_config import setup_logging
from utils.match_processing import get_predictable_matches, decide_action, print_match
from utils.file_operations import create_tip_file
from utils.cache import fetch_api_response_with_cache, get_cached_api_response
from utils.config import load_config

logger = setup_logging()
load_dotenv(override=True)

def main():
    # Ensure the cache folder exists
    os.makedirs(CACHE_FOLDER, exist_ok=True)

    parser = argparse.ArgumentParser(description="Predict matches for various sports.")
    parser.add_argument("--football", action="store_true", help="Parse only football leagues.")
    parser.add_argument("--basketball", action="store_true", help="Parse only basketball leagues.")
    parser.add_argument("--hockey", action="store_true", help="Parse only hockey leagues.")
    parser.add_argument("--cricket", action="store_true", help="Parse only cricket leagues.")
    parser.add_argument("--days", type=int, default=None, help="Number of days to fetch matches for.")
    args = parser.parse_args()

    config = load_config(CONFIG_FILE)

    # Determine which leagues to parse
    if sum([args.football, args.basketball, args.hockey, args.cricket]) > 1:
        logger.error("Cannot specify multiple sports at the same time.")
        return
    elif args.football:
        leagues = config.get("football", [])
    elif args.basketball:
        leagues = config.get("basketball", [])
    elif args.hockey:
        leagues = config.get("hockey", [])
    elif args.cricket:
        leagues = config.get("cricket", [])
    else:
        leagues = config.get("football", []) + config.get("basketball", []) + config.get("hockey", []) + config.get("cricket", [])

    nr_zile = args.days if args.days is not None else config.get("default_days", 1)
    number_of_matches = config.get("number_of_matches", 5)

    predictable_matches = get_predictable_matches(
        nr_zile=nr_zile,
        top_n=number_of_matches,
        leagues=leagues,
        fetch_api_response_with_cache=fetch_api_response_with_cache,
        get_cached_api_response=get_cached_api_response
    )
    if not predictable_matches:
        logger.info("No matches found for the specified interval or data is unavailable.")
        return

    print(f"Matches in the next {nr_zile} days from leagues: {', '.join(leagues)}")
    print("Sorted by confidence level:\n")
    for match in predictable_matches:
        action = decide_action(match, threshold=1.0)
        print_match(match, action, OUTPUT_FILE)
        create_tip_file(match, action)

if __name__ == '__main__':
    main()

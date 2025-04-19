import os
import requests
import logging

logger = logging.getLogger(__name__)

def fetch_api_response(league, api_key):
    """
    Fetches data from TheOddsAPI for a specific league.
    """
    if not api_key:
        logger.error("API key is missing. Set THE_ODDS_API_KEY in your environment.")
        return None

    url = f"https://api.the-odds-api.com/v4/sports/{league}/odds/?apiKey={api_key}&regions=eu&markets=h2h&oddsFormat=decimal"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as http_err:
        if response.status_code == 404:
            logger.error("League %s is not available (404).", league)
        else:
            logger.error("HTTP error for league %s: %s", league, http_err)
        return None
    except requests.RequestException as e:
        logger.error("API request error for league %s: %s", league, e)
        return None
    except Exception as e:
        logger.error("Unexpected error while fetching data for league %s: %s", league, e)
        return None
# Released under the MIT-0 License. Do whatever you want. No warranty.

import requests
import datetime
import os
import json
import logging
import sys
from dotenv import load_dotenv

# Configurare logare 
logging.basicConfig(
    filename='log_file.log',
    filemode='a',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()  # Încarcă variabilele de mediu

API_RESPONSE_FILE = "api_response.json"
CONFIG_FILE = "config.json"

def load_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        logger.info("Configurație încărcată din %s", CONFIG_FILE)
        return config
    except Exception as e:
        logger.error("Eroare la încărcarea configurației: %s", e)
        return {}

def get_cached_api_response(league):
    """
    Verifică dacă există cache pentru o anumită ligă (fișier separat de exemplu: api_response_{league}.json)
    și dacă este valabil pe baza datei de modificare.
    """
    cache_file = f"api_response_{league}.json"
    if os.path.exists(cache_file):
        mod_time = datetime.date.fromtimestamp(os.path.getmtime(cache_file))
        today = datetime.date.today()
        if mod_time == today:
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                logger.info("Cache pentru liga %s folosit din %s", league, cache_file)
                return data
            except Exception as e:
                logger.error("Eroare la citirea cache-ului din %s: %s", cache_file, e)
    return None

def fetch_api_response(league):
    """
    Face apelul către API pentru liga specificată și salvează răspunsul în cache specific.
    """
    api_key = os.getenv("THE_ODDS_API_KEY")
    if not api_key:
        logger.error("Cheia API lipsește. Setează THE_ODDS_API_KEY în fișierul .env")
        return None
    
    url = f"https://api.the-odds-api.com/v4/sports/{league}/odds/?apiKey={api_key}&regions=eu&markets=h2h&oddsFormat=decimal"
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.HTTPError as http_err:
        # Dacă error-ul HTTP este 404, înseamnă că liga nu este disponibilă
        if response.status_code == 404:
            logger.error("Liga %s nu este disponibilă (404).", league)
            return None
        else:
            logger.error("Eroare API pentru liga %s: %s", league, http_err)
            return None
    except requests.RequestException as e:
        logger.error("Eroare API pentru liga %s: %s", league, e)
        return None

    try:
        data = response.json()
    except Exception as e:
        logger.error("Eroare la decodificarea JSON pentru liga %s: %s", league, e)
        return None

    cache_file = f"api_response_{league}.json"
    try:
        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("Răspuns API pentru liga %s salvat în %s", league, cache_file)
    except Exception as e:
        logger.error("Eroare la scrierea cache-ului pentru liga %s: %s", league, e)
    return data

def get_matches_for_days(nr_zile=1, leagues=None):
    """
    Pentru fiecare ligă specificată, extrage meciurile din intervalul de zile,
    combinând rezultatele într-o listă comună.
    """
    if leagues is None:
        leagues = []  # sau poți returna []
    
    today = datetime.date.today()
    end_date = today + datetime.timedelta(days=nr_zile)
    combined_matches = []
    
    for league in leagues:
        # Încercăm să obținem datele din cache sau API pentru fiecare ligă.
        data = get_cached_api_response(league)
        if data is None:
            data = fetch_api_response(league)
        if data is None:
            continue

        for match in data:
            teams = match.get("teams")
            if not teams:
                team1 = match.get("home_team")
                team2 = match.get("away_team")
                if not team1 or not team2:
                    logger.warning("Meci ignorat; informații despre echipe lipsesc: %s", match)
                    continue
            else:
                team1, team2 = teams[0], teams[1]
            
            try:
                commence_time = datetime.datetime.fromisoformat(match['commence_time'].replace("Z", "+00:00")).date()
            except Exception as e:
                logger.error("Eroare la conversia datei: %s", e)
                continue

            if today <= commence_time < end_date:
                odds_team1 = []
                odds_team2 = []
                for bookmaker in match.get("bookmakers", []):
                    for market in bookmaker.get("markets", []):
                        if market.get("key") == "h2h":
                            for outcome in market.get("outcomes", []):
                                if outcome.get("name") == team1:
                                    odds_team1.append(outcome.get("price"))
                                elif outcome.get("name") == team2:
                                    odds_team2.append(outcome.get("price"))
                if odds_team1 and odds_team2:
                    best_odds_team1 = min(odds_team1)
                    best_odds_team2 = min(odds_team2)
                    match_entry = {
                        "league": league,
                        "team1": team1,
                        "team2": team2,
                        "odds": {
                            team1: best_odds_team1,
                            team2: best_odds_team2
                        },
                        "commence_time": match["commence_time"]
                    }
                    combined_matches.append(match_entry)
                    logger.debug("Meci adăugat: %s", match_entry)
                else:
                    logger.warning("Meci ignorat; cotele nu sunt complete pentru: %s vs %s", team1, team2)
    return combined_matches

def compute_predictability(match):
    """
    Calculează scorul de predictabilitate pentru un meci:
      - Se consideră favorit echipa cu cota minimă și outsider echipa cu cota maximă.
      - Diferența dintre aceste cote reprezintă scorul;
        o diferență mică indică un consens al pieței (meci predictibil).
    """
    odds = match.get('odds', {})
    if odds:
        favorite = min(odds.values())
        underdog = max(odds.values())
        score = underdog - favorite
        logger.debug("Scor predictabilitate pentru %s vs %s: %.2f", match['team1'], match['team2'], score)
        return score
    return float('inf')

def decide_action(match, threshold=1.0):
    """
    Decide acțiunea recomandată ("pariaza" sau "abtine-te") pe baza scorului de predictabilitate.
    Dacă scorul este mai mic sau egal cu threshold, se recomandă "pariaza".
    """
    predictability_score = match.get('predictability', float('inf'))
    action = "pariaza" if predictability_score <= threshold else "abtine-te"
    logger.debug("Decizie pentru %s vs %s: %s", match['team1'], match['team2'], action)
    return action

def get_predictable_matches(nr_zile=1, top_n=10, leagues=None):
    """
    Obține meciurile de fotbal ale zilei (folosind cache-ul dacă este cazul), calculează scorul de predictabilitate
    pentru fiecare și sortează lista astfel încât cele mai predictibile meciuri să fie primele.
    """
    matches = get_matches_for_days(nr_zile, leagues)
    for match in matches:
        match['predictability'] = compute_predictability(match)
    sorted_matches = sorted(matches, key=lambda m: m['predictability'])
    logger.info("Meciuri sortate după predictabilitate: %s", sorted_matches)
    return sorted_matches[:top_n]

def main():
    config = load_config()
    leagues = config.get("leagues", [])
    default_days = config.get("default_days", 1)
    
    # Preluăm argumentul din linia de comandă pentru nr_zile (dacă este specificat)
    nr_zile = default_days
    if len(sys.argv) > 1:
        try:
            nr_zile = int(sys.argv[1])
        except ValueError:
            logger.error("Argumentul pentru nr_zile nu este valid. Folosește un număr întreg.")
            return

    predictable_matches = get_predictable_matches(nr_zile=nr_zile, leagues=leagues)
    if not predictable_matches:
        logger.info("Nu s-au găsit meciuri pentru intervalul specificat sau datele nu sunt disponibile.")
        return
    
    print(f"Meciuri de fotbal în următoarele {nr_zile} zile, din ligile: {', '.join(leagues)}")
    print("Sortate după predictabilitate:\n")
    for match in predictable_matches:
        action = decide_action(match, threshold=1.0)
        try:
            commence_dt = datetime.datetime.fromisoformat(match['commence_time'].replace("Z", "+00:00"))
            commence_str = commence_dt.strftime("%d-%m-%Y %H:%M")
        except Exception as e:
            commence_str = match['commence_time']
        print("-" * 50)
        print(f"Liga:         {match['league']}")
        print(f"Echipe:       {match['team1']} vs {match['team2']}")
        print(f"Data & Oră:   {commence_str}")
        print(f"Predictabilitate: {match['predictability']:.2f}")
        print(f"Recomandare:  {action.upper()}")
        print("-" * 50 + "\n")

if __name__ == '__main__':
    main()
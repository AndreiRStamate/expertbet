# Released under the MIT-0 License. Do whatever you want. No warranty.

import requests
import datetime
import os
import json
import logging
import sys
from dotenv import load_dotenv

# Configurare logare: scrie mesajele în fișierul log_file.log
logging.basicConfig(
    filename='log_file.log',
    filemode='a',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()  # Încarcă variabilele de mediu din .env

# Folderul unde vor fi salvate fișierele de cache
CACHE_FOLDER = "cache"

# Asigură-te că folderul de cache există
os.makedirs(CACHE_FOLDER, exist_ok=True)

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
    Verifică dacă există cache pentru liga specificată.
    Cache-ul este salvat în fișierul: cache/api_response_{league}.json
    și este considerat valid dacă data ultimei modificări este egală cu ziua curentă.
    """
    cache_file = os.path.join(CACHE_FOLDER, f"api_response_{league}.json")
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
    Face apelul către API-ul TheOddsAPI pentru liga specificată și salvează răspunsul brut
    în cache (fișierul cache/api_response_{league}.json).
    """
    api_key = os.getenv("THE_ODDS_API_KEY")
    if not api_key:
        logger.error("Cheia API lipsește. Setează THE_ODDS_API_KEY în .env")
        return None
    
    url = f"https://api.the-odds-api.com/v4/sports/{league}/odds/?apiKey={api_key}&regions=eu&markets=h2h&oddsFormat=decimal"
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.HTTPError as http_err:
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

    cache_file = os.path.join(CACHE_FOLDER, f"api_response_{league}.json")
    try:
        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("Răspuns API pentru liga %s salvat în %s", league, cache_file)
    except Exception as e:
        logger.error("Eroare la scrierea cache-ului pentru liga %s: %s", league, e)
    return data

def get_matches_for_days(nr_zile=1, leagues=None):
    """
    Pentru fiecare ligă specificată, extrage meciurile din intervalul de zile [today, today + nr_zile)
    și combină rezultatele într-o listă comună.
    """
    if leagues is None:
        leagues = []
    
    today = datetime.date.today()
    end_date = today + datetime.timedelta(days=nr_zile)
    combined_matches = []
    
    for league in leagues:
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
    Decide acțiunea recomandată ("Pariu sigur" sau "Pariu riscant") pe baza scorului de predictabilitate.
    Dacă scorul este mai mic sau egal cu threshold, se recomandă "Pariu sigur".
    """
    predictability_score = match.get('predictability', float('inf'))
    action = "Pariu sigur" if predictability_score <= threshold else "Pariu riscant"
    logger.debug("Decizie pentru %s vs %s: %s", match['team1'], match['team2'], action)
    return action

def get_predictable_matches(nr_zile=1, top_n=-1, leagues=None):
    """
    Obține meciurile de fotbal ale zilei (folosind cache-ul dacă este cazul), calculează scorul de predictabilitate
    pentru fiecare și sortează lista astfel încât cele mai predictibile meciuri să fie primele.
    """
    matches = get_matches_for_days(nr_zile, leagues)
    for match in matches:
        match['predictability'] = compute_predictability(match)
    sorted_matches = sorted(matches, key=lambda m: m['predictability'])
    logger.info("Meciuri sortate după predictabilitate: %s", sorted_matches)
    if top_n == -1:
        top_n = len(sorted_matches)
    return sorted_matches[:top_n]

def print_match(match, action):
    # Convertim data din format ISO într-un format prietenos
    try:
        commence_dt = datetime.datetime.fromisoformat(match['commence_time'].replace("Z", "+00:00"))
        commence_str = commence_dt.strftime("%d-%m-%Y %H:%M")
    except Exception as e:
        commence_str = match['commence_time']

    # Setări pentru afișare
    total_width = 60        # Lățimea totală a liniei, inclusiv marginile
    content_width = total_width - 2  # Spațiul interior dintre marginile '|'
    label_width = 20        # Lățime rezervată pentru etichete
    value_width = content_width - label_width  # Spațiul rezervat pentru valori

    border = "+" + "-" * (total_width - 2) + "+"

    def format_row(label, value):
        # Convertim valoarea la string
        str_value = str(value)
        # Dacă valoarea este prea lungă, o trunchiem și adăugăm "..."
        if len(str_value) > value_width:
            str_value = str_value[:value_width-3] + "..."
        # Formatează rândul cu eticheta aliniată la stânga și valoarea la dreapta
        return f"|{label:<{label_width}}{str_value:>{value_width}}|"

    print(border)
    print(format_row("Liga:", match['league']))
    print(format_row("Echipe:", f"{match['team1']} vs {match['team2']}"))
    print(format_row("Data & Oră:", commence_str))
    print(format_row("Predictabilitate:", f"{match['predictability']:.2f}"))
    print(format_row("Evaluare:", action.upper()))
    print(border)

def main():
    config = load_config()
    leagues = config.get("leagues", [])
    default_days = config.get("default_days", 1)
    number_of_matches = config.get("number_of_matches", 5)
    
    # Preluăm argumentul din linia de comandă pentru nr_zile (dacă este specificat)
    nr_zile = default_days
    if len(sys.argv) > 1:
        try:
            nr_zile = int(sys.argv[1])
        except ValueError:
            logger.error("Argumentul pentru nr_zile nu este valid. Folosește un număr întreg.")
            return

    predictable_matches = get_predictable_matches(nr_zile=nr_zile, top_n=number_of_matches, leagues=leagues)
    if not predictable_matches:
        logger.info("Nu s-au găsit meciuri pentru intervalul specificat sau datele nu sunt disponibile.")
        return
    
    print(f"Meciuri de fotbal în următoarele {nr_zile} zile, din ligile: {', '.join(leagues)}")
    print("Sortate după gradul de încredere:\n")
    for match in predictable_matches:
        action = decide_action(match, threshold=1.0)
        print_match(match, action)

if __name__ == '__main__':
    main()

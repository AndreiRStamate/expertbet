# Released under the MIT-0 License. Do whatever you want. No warranty.

import requests
import datetime
import os
import json
import logging
import sys
from dotenv import load_dotenv
import stat  # Add this import at the top of the file
import argparse  # Add this import for argument parsing

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

LEAGUE_NAMES = {
    "soccer_argentina_primera_division": "Argentina Primera Division",
    "soccer_australia_aleague": "Australia A-League",
    "soccer_austria_bundesliga": "Austria Bundesliga",
    "soccer_belgium_first_div": "Belgium First Division",
    "soccer_brazil_campeonato": "Brazil Campeonato",
    "soccer_brazil_serie_b": "Brazil Serie B",
    "soccer_chile_campeonato": "Chile Campeonato",
    "soccer_china_superleague": "China Super League",
    "soccer_conmebol_copa_libertadores": "CONMEBOL Copa Libertadores",
    "soccer_conmebol_copa_sudamericana": "CONMEBOL Copa Sudamericana",
    "soccer_denmark_superliga": "Denmark Superliga",
    "soccer_efl_champ": "EFL Championship",
    "soccer_england_league1": "England League One",
    "soccer_england_league2": "England League Two",
    "soccer_epl": "English Premier League",
    "soccer_fa_cup": "FA Cup",
    "soccer_finland_veikkausliiga": "Finland Veikkausliiga",
    "soccer_france_ligue_one": "France Ligue 1",
    "soccer_france_ligue_two": "France Ligue 2",
    "soccer_germany_bundesliga": "Germany Bundesliga",
    "soccer_germany_bundesliga2": "Germany Bundesliga 2",
    "soccer_germany_liga3": "Germany Liga 3",
    "soccer_greece_super_league": "Greece Super League",
    "soccer_italy_serie_a": "Italy Serie A",
    "soccer_italy_serie_b": "Italy Serie B",
    "soccer_japan_j_league": "Japan J-League",
    "soccer_korea_kleague1": "Korea K-League 1",
    "soccer_league_of_ireland": "League of Ireland",
    "soccer_mexico_ligamx": "Mexico Liga MX",
    "soccer_netherlands_eredivisie": "Netherlands Eredivisie",
    "soccer_norway_eliteserien": "Norway Eliteserien",
    "soccer_poland_ekstraklasa": "Poland Ekstraklasa",
    "soccer_portugal_primeira_liga": "Portugal Primeira Liga",
    "soccer_spain_la_liga": "La Liga",
    "soccer_spain_segunda_division": "Spain Segunda Division",
    "soccer_sweden_allsvenskan": "Sweden Allsvenskan",
    "soccer_sweden_superettan": "Sweden Superettan",
    "soccer_switzerland_superleague": "Switzerland Super League",
    "soccer_turkey_super_league": "Turkey Super League",
    "soccer_uefa_champs_league": "UEFA Champions League",
    "soccer_uefa_champs_league_women": "UEFA Champions League Women",
    "soccer_uefa_europa_conference_league": "UEFA Europa Conference League",
    "soccer_uefa_europa_league": "UEFA Europa League",
    "soccer_uefa_nations_league": "UEFA Nations League",
    "soccer_usa_mls": "USA Major League Soccer"
}

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
    Cache-ul este salvat în fișierul: cache/sport/api_response_{league}.json
    și este considerat valid dacă data ultimei modificări este egală cu ziua curentă.
    """
    sport_folder = "soccer" if "soccer" in league else "basketball"
    cache_folder = os.path.join(CACHE_FOLDER, sport_folder)
    os.makedirs(cache_folder, exist_ok=True)  # Ensure the sport-specific folder exists

    cache_file = os.path.join(cache_folder, f"api_response_{league}.json")
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
    în cache (fișierul cache/sport/api_response_{league}.json).
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

    sport_folder = "soccer" if "soccer" in league else "basketball"
    cache_folder = os.path.join(CACHE_FOLDER, sport_folder)
    os.makedirs(cache_folder, exist_ok=True)  # Ensure the sport-specific folder exists

    cache_file = os.path.join(cache_folder, f"api_response_{league}.json")
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

def print_match(match, action, output_file=None):
    """
    Prints match details to the terminal and optionally writes them to an output file.
    """
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

    # Build the match details as a string
    match_details = "\n".join([
        border,
        format_row("Liga:", match['league']),
        format_row("Echipe:", f"{match['team1']} vs {match['team2']}"),
        format_row("Data & Oră:", commence_str),
        format_row("Predictabilitate:", f"{match['predictability']:.2f}"),
        format_row("Evaluare:", action.upper()),
        border
    ])

    # Print to terminal
    print(match_details)

    # Write to the output file
    if output_file:
        try:
            with open(output_file, "a") as f:
                f.write(match_details + "\n\n")  # Add a newline between matches
            logger.info("Match details written to %s", output_file)
        except Exception as e:
            logger.error("Failed to write match details to %s: %s", output_file, e)

def create_tip_file(match, action, template_file="prompt-examples/gpt-generated-5x3.txt"):
    """
    Creates a tip file for a match with the action 'pariu sigur'.
    The file is generated based on a template file with placeholders replaced by match details.
    """
    if action.lower() != "pariu sigur":
        return

    # Ensure the 'ponturi' folder exists
    ponturi_folder = "ponturi"
    os.makedirs(ponturi_folder, exist_ok=True)

    # Read the template content from the file
    try:
        with open(template_file, 'r') as f:
            template_content = f.read()
    except Exception as e:
        logger.error("Failed to read template file %s: %s", template_file, e)
        return

    # Get the human-readable league name
    league_name = LEAGUE_NAMES.get(match['league'], match['league'])

    # Replace placeholders in the template with match details
    filled_content = template_content.format(
        team1=match['team1'],
        team2=match['team2'],
        sport_title=league_name,
        commence_time=match['commence_time']
    )

    # Generate a unique filename for the tip
    filename = f"tip_{match['team1'].replace(' ', '_')}_vs_{match['team2'].replace(' ', '_')}.txt"
    filepath = os.path.join(ponturi_folder, filename)

    # Write the filled content to the file
    try:
        with open(filepath, 'w') as f:
            f.write(filled_content.strip())
        # Set the file to read-only
        os.chmod(filepath, stat.S_IREAD)
        logger.info("Tip file created and set to read-only: %s", filepath)
    except Exception as e:
        logger.error("Failed to create tip file for %s vs %s: %s", match['team1'], match['team2'], e)

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Predict football or basketball matches.")
    parser.add_argument("--football", action="store_true", help="Parse only football leagues.")
    parser.add_argument("--basketball", action="store_true", help="Parse only basketball leagues.")
    parser.add_argument("--days", type=int, default=None, help="Number of days to fetch matches for.")
    args = parser.parse_args()

    config = load_config()

    # Determine which leagues to parse based on the arguments
    if args.football and args.basketball:
        logger.error("Cannot specify both --football and --basketball at the same time.")
        return
    elif args.football:
        leagues = config.get("football", [])
    elif args.basketball:
        leagues = config.get("basketball", [])
    else:
        leagues = config.get("football", []) + config.get("basketball", [])

    # Use the specified number of days or the default from the config
    nr_zile = args.days if args.days is not None else config.get("default_days", 1)
    number_of_matches = config.get("number_of_matches", 5)

    predictable_matches = get_predictable_matches(nr_zile=nr_zile, top_n=number_of_matches, leagues=leagues)
    if not predictable_matches:
        logger.info("No matches found for the specified interval or data is unavailable.")
        return

    print(f"Matches in the next {nr_zile} days from leagues: {', '.join(leagues)}")
    print("Sorted by confidence level:\n")
    for match in predictable_matches:
        action = decide_action(match, threshold=1.0)
        print_match(match, action)
        create_tip_file(match, action)

if __name__ == '__main__':
    main()

# Released under the MIT-0 License. Do whatever you want. No warranty.

import requests
import datetime
import os
import json
import logging
import sys
from dotenv import load_dotenv  # Import load_dotenv

# Configurare logare
logging.basicConfig(
    filename='log_file.log',  # toate mesajele vor fi scrise aici
    filemode='a',             # a = append, w = overwrite
    level=logging.DEBUG,      # nivelul poate fi ajustat: DEBUG, INFO, etc.
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()  # Load environment variables from .env file

API_RESPONSE_FILE = "api_response.json"

def get_cached_api_response():
    """
    Verifică dacă fișierul api_response.json există și dacă data ultimei modificări
    este egală cu ziua curentă. Dacă da, încarcă și returnează conținutul JSON.
    """
    if os.path.exists(API_RESPONSE_FILE):
        # Obținem data ultimei modificări a fișierului
        mod_time = datetime.date.fromtimestamp(os.path.getmtime(API_RESPONSE_FILE))
        today = datetime.date.today()
        if mod_time == today:
            try:
                with open(API_RESPONSE_FILE, 'r') as f:
                    data = json.load(f)
                logger.info("Se folosește cache din %s", API_RESPONSE_FILE)
                return data
            except Exception as e:
                logger.error("Eroare la citirea fișierului %s: %s", API_RESPONSE_FILE, e)
    return None

def fetch_api_response():
    """
    Face apelul către API-ul TheOddsAPI și salvează răspunsul brut în fișierul api_response.json.
    """
    api_key = os.getenv("THE_ODDS_API_KEY")
    if not api_key:
        logger.error("API key is missing. Please set THE_ODDS_API_KEY environment variable.")
        return None
    
    url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?apiKey={api_key}&regions=eu&markets=h2h&oddsFormat=decimal"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error("A apărut o eroare la obținerea datelor din API: %s", e)
        return None

    try:
        data = response.json()
    except Exception as e:
        logger.error("Eroare la decodificarea răspunsului JSON: %s", e)
        return None
    
    try:
        with open(API_RESPONSE_FILE, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("Răspunsul API a fost salvat în %s", API_RESPONSE_FILE)
    except Exception as e:
        logger.error("Eroare la scrierea în %s: %s", API_RESPONSE_FILE, e)
    
    return data

def get_matches_for_days(nr_zile=1):
    """
    Extrage meciurile de fotbal pentru un interval de zile, începând cu ziua curentă
    și incluzând următoarele (nr_zile - 1) zile.
    
    Se folosește cache-ul din api_response.json dacă acesta este actual.
    """
    today = datetime.date.today()
    end_date = today + datetime.timedelta(days=nr_zile)
    
    data = get_cached_api_response()
    if data is None:
        data = fetch_api_response()
        if data is None:
            logger.error("Nu s-au putut obține date de la API.")
            return []
    
    matches_interval = []
    
    for match in data:
        # Obținem denumirile echipelor: încercăm mai întâi cheia "teams".
        teams = match.get("teams")
        if not teams:
            team1 = match.get("home_team")
            team2 = match.get("away_team")
            if not team1 or not team2:
                logger.warning("Meci ignorat; informații despre echipe lipsesc: %s", match)
                continue
        else:
            team1, team2 = teams[0], teams[1]
        
        # Convertim ora de începere într-un obiect date.
        try:
            commence_time = datetime.datetime.fromisoformat(match['commence_time'].replace("Z", "+00:00")).date()
        except Exception as e:
            logger.error("Eroare la conversia datei pentru meci: %s", e)
            continue
        # Dacă meciul se desfășoară în intervalul specificat, îl adăugăm.
        if today <= commence_time < end_date:
            odds_team1 = []
            odds_team2 = []
            # Parcurgem fiecare bookmaker pentru a obține cotele din piața "h2h"
            for bookmaker in match.get("bookmakers", []):
                for market in bookmaker.get("markets", []):
                    if market.get("key") == "h2h":
                        for outcome in market.get("outcomes", []):
                            if outcome.get("name") == team1:
                                odds_team1.append(outcome.get("price"))
                            elif outcome.get("name") == team2:
                                odds_team2.append(outcome.get("price"))
            # Dacă avem cotele pentru ambele echipe, alegem cele mai avantajoase (minime)
            if odds_team1 and odds_team2:
                best_odds_team1 = min(odds_team1)
                best_odds_team2 = min(odds_team2)
                match_entry = {
                    "team1": team1,
                    "team2": team2,
                    "odds": {
                        team1: best_odds_team1,
                        team2: best_odds_team2
                    },
                    "commence_time": match["commence_time"]
                }
                matches_interval.append(match_entry)
                logger.debug("Meci adăugat: %s", match_entry)
            else:
                logger.warning("Meci ignorat; cotele nu sunt complete pentru: %s vs %s", team1, team2)
    
    return matches_interval

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

def get_predictable_matches(nr_zile=1, top_n=10):
    """
    Obține meciurile de fotbal ale zilei (folosind cache-ul dacă este cazul), calculează scorul de predictabilitate
    pentru fiecare și sortează lista astfel încât cele mai predictibile meciuri să fie primele.
    """
    matches = get_matches_for_days(nr_zile)
    for match in matches:
        match['predictability'] = compute_predictability(match)
    sorted_matches = sorted(matches, key=lambda m: m['predictability'])
    logger.info("Meciuri sortate după predictabilitate: %s", sorted_matches)
    return sorted_matches[:top_n]

def main():
    # Preluăm argumentul din linia de comandă pentru nr_zile; implicit 1 dacă nu este specificat.
    nr_zile = 1
    if len(sys.argv) > 1:
        try:
            nr_zile = int(sys.argv[1])
        except ValueError:
            logger.error("Argumentul nu este valid. Folosește un număr întreg pentru nr_zile.")
            return
    
    predictable_matches = get_predictable_matches(nr_zile=nr_zile)
    if not predictable_matches:
        logger.info("Nu s-au găsit meciuri pentru intervalul specificat sau datele nu sunt disponibile.")
        return
    
    print(f"Meciuri de fotbal în următoarele {nr_zile} zile, sortate după predictabilitate:\n")
    for match in predictable_matches:
        action = decide_action(match, threshold=1.0)
        # Convertim ora de începere într-un format mai prietenos, ex: "14-04-2025 19:00"
        try:
            commence_dt = datetime.datetime.fromisoformat(match['commence_time'].replace("Z", "+00:00"))
            commence_str = commence_dt.strftime("%d-%m-%Y %H:%M")
        except Exception as e:
            commence_str = match['commence_time']
        
        print("-" * 50)
        print(f"Echipe:       {match['team1']} vs {match['team2']}")
        print(f"Data & Oră:   {commence_str}")
        print(f"Predictabilitate: {match['predictability']:.2f}")
        print(f"Recomandare:  {action.upper()}")
        print("-" * 50 + "\n")

if __name__ == '__main__':
    main()

import requests
import datetime
import os
import json
import logging
from dotenv import load_dotenv  # Import load_dotenv

# Configurare logare
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
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

def get_todays_matches():
    """
    Extrage meciurile de fotbal ale zilei folosind cache-ul din api_response.json.
    Dacă cache-ul nu există sau nu este valid (nu are data curentă),
    face apelul către API și salvează răspunsul în fișierul de cache.
    Apoi procesează conținutul și returnează meciurile filtrate pe ziua curentă.
    """
    today = datetime.date.today()
    
    data = get_cached_api_response()
    if data is None:
        data = fetch_api_response()
        if data is None:
            logger.error("Nu s-au putut obține date de la API.")
            return []
    
    # Procesăm datele pentru a extrage meciurile de astăzi.
    matches_today = []
    
    for match in data:
        # Obținem denumirile echipelor: încercăm mai întâi cheia "teams".
        teams = match.get("teams")
        if not teams:
            # Dacă nu există "teams", încercăm cheile alternative "home_team" și "away_team".
            team1 = match.get("home_team")
            team2 = match.get("away_team")
            if not team1 or not team2:
                logger.warning("Meci ignorat; informații despre echipe lipsesc: %s", match)
                continue
        else:
            team1, team2 = teams[0], teams[1]
        
        # Convertim ora de începere într-un obiect date.
        commence_time = datetime.datetime.fromisoformat(match['commence_time'].replace("Z", "+00:00")).date()
        if commence_time == today:
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
                matches_today.append(match_entry)
                logger.debug("Meci adăugat: %s", match_entry)
            else:
                logger.warning("Meci ignorat; cotele nu sunt complete pentru: %s vs %s", team1, team2)
    
    return matches_today

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

def get_predictable_matches(top_n=10):
    """
    Obține meciurile de fotbal ale zilei (folosind cache-ul dacă este cazul), calculează scorul de predictabilitate
    pentru fiecare și sortează lista astfel încât cele mai predictibile meciuri să fie primele.
    """
    matches = get_todays_matches()
    for match in matches:
        match['predictability'] = compute_predictability(match)
    sorted_matches = sorted(matches, key=lambda m: m['predictability'])
    logger.info("Meciuri sortate după predictabilitate: %s", sorted_matches)
    return sorted_matches[:top_n]

def main():
    predictable_matches = get_predictable_matches()
    if not predictable_matches:
        logger.info("Nu s-au găsit meciuri pentru ziua de azi sau datele nu sunt disponibile.")
        return
    
    print("Meciuri de fotbal ale zilei (date reale), sortate după predictabilitate:")
    for match in predictable_matches:
        action = decide_action(match, threshold=1.0)
        print(f"{match['team1']} vs {match['team2']} - Cotele: {match['odds']} - Scor predictabilitate: {match['predictability']:.2f} -> Recomandare: {action}")

if __name__ == '__main__':
    main()

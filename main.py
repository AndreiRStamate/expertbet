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

CACHE_FILE = "cache_matches.json"
API_RESPONSE_FILE = "api_response.json"  # Noul fișier în care vom salva răspunsul API

def get_todays_matches():
    """
    Extrage meciurile de fotbal ale zilei din API-ul TheOddsAPI,
    utilizând un mecanism de cache pentru a reduce numărul de apeluri.

    Verifică dacă pentru un eveniment există cheia 'teams'. Dacă nu, încearcă
    să extragă echipele din 'home_team' și 'away_team'. Dacă nici acestea nu
    sunt disponibile, meciul este ignorat.
    """
    today = datetime.date.today()
    today_str = today.strftime("%Y-%m-%d")
    
    # Încercăm să folosim datele din cache dacă există și sunt pentru ziua curentă.
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                cache_data = json.load(f)
            if cache_data.get("date") == today_str:
                logger.info("Utilizare cache pentru meciurile din ziua de azi.")
                return cache_data.get("matches", [])
        except Exception as e:
            logger.error("Eroare la citirea fișierului de cache: %s", e)
    
    # Retrieve API key from environment variable
    api_key = os.getenv("THE_ODDS_API_KEY")
    if not api_key:
        logger.error("API key is missing. Please set the THE_ODDS_API_KEY environment variable.")
        return []
    
    url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?apiKey={api_key}&regions=eu&markets=h2h&oddsFormat=decimal"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error("A apărut o eroare la obținerea datelor din API: %s", e)
        return []
    
    # Obținem răspunsul API și salvăm conținutul brut într-un fișier nou
    data = response.json()
    try:
        with open(API_RESPONSE_FILE, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("Răspunsul API a fost salvat în fișierul %s", API_RESPONSE_FILE)
    except Exception as e:
        logger.error("Eroare la scrierea răspunsului API în %s: %s", API_RESPONSE_FILE, e)

    logger.debug("API response data: %s", json.dumps(data, indent=2, ensure_ascii=False))
    
    matches_today = []
    
    for match in data:
        # Obținem denumirile echipelor: încercăm mai întâi cheia "teams".
        teams = match.get("teams")
        if not teams:
            # Dacă nu există "teams", încercăm cheile alternative "home_team" și "away_team".
            team1 = match.get("home_team")
            team2 = match.get("away_team")
            if not team1 or not team2:
                logger.warning("Meci ignorat; nu s-au găsit informații despre echipe: %s", match)
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
                logger.warning("Meci ignorat; cotele nu sunt complete pentru meci: %s vs %s", team1, team2)
    
    # Salvăm rezultatele în cache împreună cu data curentă.
    cache_data = {"date": today_str, "matches": matches_today}
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache_data, f)
        logger.info("Cache salvat cu succes.")
    except Exception as e:
        logger.error("Eroare la scrierea în cache: %s", e)
    
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
        logger.info("Nu s-au găsit meciuri pentru ziua de azi sau API-ul nu a returnat date.")
        return
    
    print("Meciuri de fotbal ale zilei (date reale), sortate după predictabilitate:")
    for match in predictable_matches:
        action = decide_action(match, threshold=1.0)
        print(f"{match['team1']} vs {match['team2']} - Cotele: {match['odds']} - Scor predictabilitate: {match['predictability']:.2f} -> Recomandare: {action}")

if __name__ == '__main__':
    main()

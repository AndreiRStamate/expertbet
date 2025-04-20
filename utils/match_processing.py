import datetime
import logging

logger = logging.getLogger(__name__)

def get_matches_for_days(nr_zile=1, leagues=None, get_api_data=None, get_cached_data=None):
    """
    Extracts matches for the specified leagues within the interval [today, today + nr_zile).
    Combines results into a single list.
    """
    if leagues is None:
        leagues = []
    
    today = datetime.date.today()
    end_date = today + datetime.timedelta(days=nr_zile)
    combined_matches = []
    
    for league in leagues:
        data = get_cached_data(league)
        if data is None:
            data = get_api_data(league)
        if data is None:
            continue

        for match in data:
            teams = match.get("teams")
            if not teams:
                team1 = match.get("home_team")
                team2 = match.get("away_team")
                if not team1 or not team2:
                    logger.warning("Match ignored; missing team information: %s", match)
                    continue
            else:
                team1, team2 = teams[0], teams[1]
            
            try:
                commence_time = datetime.datetime.fromisoformat(match['commence_time'].replace("Z", "+00:00")).date()
            except Exception as e:
                logger.error("Error converting date: %s", e)
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
                    logger.debug("Match added: %s", match_entry)
                else:
                    logger.warning("Match ignored; incomplete odds for: %s vs %s", team1, team2)
    for match in combined_matches:
        match['predictability'] = compute_predictability(match)
    return combined_matches

def compute_predictability(match):
    """
    Calculates the predictability score for a match:
      - The favorite is the team with the lowest odds, and the underdog has the highest odds.
      - The difference between these odds represents the score;
        a small difference indicates market consensus (predictable match).
    """
    odds = match.get('odds', {})
    if odds:
        favorite = min(odds.values())
        underdog = max(odds.values())
        score = underdog - favorite
        logger.debug("Predictability score for %s vs %s: %.2f", match['team1'], match['team2'], score)
        return score
    return float('inf')

def decide_action(match, threshold=1.0):
    """
    Decides the recommended action ("Pariu sigur" or "Pariu riscant") based on the predictability score.
    If the score is less than or equal to the threshold, "Pariu sigur" is recommended.
    """
    predictability_score = match.get('predictability', float('inf'))
    action = "Pariu sigur" if predictability_score <= threshold else "Pariu riscant"
    logger.debug("Decision for %s vs %s: %s", match['team1'], match['team2'], action)
    return action

def get_matches_sorted(by, nr_zile=1, top_n=-1, leagues=None, get_api_data=None, get_cached_data=None):
    """
    Retrieves matches for the specified number of days, sorts them by a specified attribute,
    applies a mutation function if provided, and returns the top N matches.
    """
    matches = get_matches_for_days(nr_zile, leagues, get_api_data, get_cached_data)
    sorted_matches = sorted(matches, key=lambda m: m[by])
    logger.info("Matches sorted by %s: %s", by, sorted_matches)
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

    # Write to the output file
    if output_file:
        try:
            with open(output_file, "a") as f:
                f.write(match_details + "\n\n")  # Add a newline between matches
            logger.info("Match details written to %s", output_file)
        except Exception as e:
            logger.error("Failed to write match details to %s: %s", output_file, e)

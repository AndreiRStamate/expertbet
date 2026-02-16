import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

def to_compact_matches(raw: Any) -> List[Dict[str, Any]]:
    """
    Convert TheOddsAPI raw response (list of matches) into compact matches.

    Strict mode:
      - skip match unless odds_home, odds_away, odds_draw are ALL present
      - odds are MIN across all bookmakers for market key == "h2h"
    """
    if not isinstance(raw, list):
        return []

    compact: List[Dict[str, Any]] = []

    for match in raw:
        if not isinstance(match, dict):
            continue

        match_id = match.get("id")
        sport_key = match.get("sport_key")
        sport_title = match.get("sport_title")
        commence_time = match.get("commence_time")
        home_team = match.get("home_team")
        away_team = match.get("away_team")

        # Required base fields
        if not all([match_id, sport_key, sport_title, commence_time, home_team, away_team]):
            continue

        odds_home_candidates: List[float] = []
        odds_away_candidates: List[float] = []
        odds_draw_candidates: List[float] = []

        bookmakers = match.get("bookmakers") or []
        if isinstance(bookmakers, list):
            for bookmaker in bookmakers:
                if not isinstance(bookmaker, dict):
                    continue
                markets = bookmaker.get("markets") or []
                if not isinstance(markets, list):
                    continue

                for market in markets:
                    if not isinstance(market, dict):
                        continue
                    if market.get("key") != "h2h":
                        continue

                    outcomes = market.get("outcomes") or []
                    if not isinstance(outcomes, list):
                        continue

                    for outcome in outcomes:
                        if not isinstance(outcome, dict):
                            continue
                        name = outcome.get("name")
                        price = outcome.get("price")

                        if not isinstance(price, (int, float)) or not isinstance(name, str):
                            continue

                        if name == home_team:
                            odds_home_candidates.append(float(price))
                        elif name == away_team:
                            odds_away_candidates.append(float(price))
                        elif name == "Draw":
                            odds_draw_candidates.append(float(price))

        # Strict: require all 3
        if not odds_home_candidates or not odds_away_candidates or not odds_draw_candidates:
            continue

        compact.append({
            "id": match_id,
            "sport_key": sport_key,
            "sport_title": sport_title,
            "commence_time": commence_time,
            "home_team": home_team,
            "away_team": away_team,
            "odds_home": min(odds_home_candidates),
            "odds_away": min(odds_away_candidates),
            "odds_draw": min(odds_draw_candidates),
        })

    return compact
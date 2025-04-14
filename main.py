def get_todays_matches():
    """
    Returnează o listă de meciuri mock-uite pentru ziua curentă.
    Fiecare meci este reprezentat ca un dicționar cu:
      - 'team1' și 'team2': numele echipelor
      - 'odds': un dicționar cu cotele oferite pentru fiecare echipă
    """
    matches = [
        {
            'team1': 'Steaua București',
            'team2': 'Dinamo București',
            'odds': {'team1': 1.80, 'team2': 4.50}
        },
        {
            'team1': 'FC Botoșani',
            'team2': 'CFR Cluj',
            'odds': {'team1': 3.20, 'team2': 1.50}
        },
        {
            'team1': 'Universitatea Craiova',
            'team2': 'Sepsi Sfântu Gheorghe',
            'odds': {'team1': 2.10, 'team2': 2.90}
        }
    ]
    return matches

def compute_predictability(match):
    """
    Calculează scorul de predictabilitate pentru un meci.
    Se identifică cota favorită (minim) și cea a outsiderului (maxim),
    iar diferența dintre ele reprezintă "scorul".
      - Cu o diferență mică, meciul poate fi considerat mai predictibil.
    """
    odds = match.get('odds', {})
    if odds:
        favorite = min(odds.values())
        underdog = max(odds.values())
        score = underdog - favorite
        return score
    return float('inf')

def decide_action(match, threshold=1.0):
    """
    Decide dacă pentru un meci se recomandă "pariaza" sau "abtine-te" 
    în funcție de scorul de predictabilitate și de un prag.
    
    Parametri:
      - match: dicționarul meciului, care conține și cheia 'predictability'
      - threshold: pragul de decizie; dacă scorul este <= threshold, 
                   se recomandă "pariaza", altfel "abtine-te".
    """
    predictability_score = match.get('predictability', float('inf'))
    if predictability_score <= threshold:
        return "pariaza"
    else:
        return "abtine-te"

def get_predictable_matches(top_n=10):
    """
    Obține lista meciurilor, calculează pentru fiecare scorul de predictabilitate,
    sortează meciurile în funcție de acest scor (cele mai mici scoruri înseamnă
    meciuri mai "predictibile") și returnează primele top_n meciuri.
    """
    matches = get_todays_matches()
    for match in matches:
        match['predictability'] = compute_predictability(match)
    # Sortează meciurile; cu cât scorul este mai mic, meciul este considerat mai predictibil
    sorted_matches = sorted(matches, key=lambda m: m['predictability'])
    return sorted_matches[:top_n]

def main():
    predictable_matches = get_predictable_matches()
    print("Meciuri de fotbal ale zilei, sortate după predictabilitate:")
    for match in predictable_matches:
        # Determinăm acțiunea recomandată în funcție de scorul de predictabilitate.
        action = decide_action(match, threshold=1.0)
        print(f"{match['team1']} vs {match['team2']} - Scor predictabilitate: {match['predictability']:.2f} -> Recomandare: {action}")

if __name__ == '__main__':
    main()

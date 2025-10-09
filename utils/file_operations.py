import os
import stat
import logging

logger = logging.getLogger(__name__)

def sanitize_filename(name):
    return name.replace("/", "_").replace("\\", "_").replace(":", "_").replace("*", "_").replace("?", "_").replace("\"", "_").replace("<", "_").replace(">", "_").replace("|", "_")

def get_template_from_sport(sport):
    templates = {
        "football": "prompt-examples/gpt-generated-5x3.txt",
        "basketball": "prompt-examples/gpt-generated-basketball.txt"
    }
    return templates.get(sport, "prompt-examples/gpt-generated-5x3.txt")

def create_tip_file(match, action, sport):
    # if action.lower() != "pariu sigur":
    #     return
    template_file = get_template_from_sport(sport)
    # Get the absolute path for the ponturi folder
    base_dir = os.path.dirname(os.path.abspath(__file__))  # Get the directory of this script
    ponturi_folder = os.path.join(base_dir, "..", "ponturi")  # Navigate to the parent directory and create "ponturi"
    os.makedirs(ponturi_folder, exist_ok=True)

    # Get the absolute path for the template file
    template_file_path = os.path.join(base_dir, "..", template_file)

    try:
        with open(template_file_path, 'r') as f:
            template_content = f.read()
    except Exception as e:
        logger.error("Failed to read template file %s: %s", template_file_path, e)
        return

    filled_content = template_content.format(
        team1=match['team1'],
        team2=match['team2'],
        sport_title=match['league'],
        commence_time=match['commence_time']
    )

    sanitized_team1 = sanitize_filename(match['team1'])
    sanitized_team2 = sanitize_filename(match['team2'])
    filename = f"tip_{sanitized_team1}_vs_{sanitized_team2}.txt"
    filepath = os.path.join(ponturi_folder, filename)

    try:
        with open(filepath, 'w') as f:
            f.write(filled_content.strip())
        os.chmod(filepath, stat.S_IREAD)
        logger.info("Tip file created: %s", filepath)
    except Exception as e:
        logger.error("Failed to create tip file: %s", e)

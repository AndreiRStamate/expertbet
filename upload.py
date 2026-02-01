import requests
import os

API_KEY = os.environ["API_KEY"]

def upload(folder, url):
    for name in os.listdir(folder):
        if name.endswith(".json"):
            path = os.path.join(folder, name)
            print(f"→ Uploading {name}")
            with open(path, "rb") as f:
                requests.post(
                    url,
                    headers={"X-API-KEY": API_KEY},
                    files={"file": f},
                )

upload("data/cache/football", "https://small-artifactory.fly.dev/football/upload")
# upload("data/cache/basketball", "https://small-artifactory.fly.dev/basketball/upload")
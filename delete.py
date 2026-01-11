import requests
import os

API_KEY = os.environ["API_KEY"]

def delete_all(folder, url):
    requests.delete(
                    url,
                    headers={"X-API-KEY": API_KEY}
                )
                

delete_all("/workspace/cache/football", "https://small-artifactory.fly.dev/football/delete_all")
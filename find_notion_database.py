import os
import requests
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

response = requests.post(
    "https://api.notion.com/v1/search",
    headers=headers,
    json={
        "filter": {
            "property": "object",
            "value": "database"
        },
        "page_size": 20
    },
    timeout=30,
)

print("Status:", response.status_code)

if not response.ok:
    print(response.text)
    response.raise_for_status()

data = response.json()

for item in data.get("results", []):
    title_parts = item.get("title", [])
    title = "".join(part.get("plain_text", "") for part in title_parts)
    print()
    print("Title:", title)
    print("ID:", item.get("id"))
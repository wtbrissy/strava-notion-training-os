import os
from pathlib import Path

import requests
from dotenv import load_dotenv, set_key


# =========================
# Settings
# =========================

ENV_FILE = Path(__file__).with_name(".env")
load_dotenv(dotenv_path=ENV_FILE)

STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
STRAVA_REFRESH_TOKEN = os.getenv("STRAVA_REFRESH_TOKEN")

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

NOTION_VERSION = "2022-06-28"

# Strava max per_page is 200
PER_PAGE = 20

# None = sync all activities
# Example: set to 2 if you only want first 2 pages for testing
MAX_PAGES = 1


# =========================
# Basic helpers
# =========================

def require_env(name, value):
    if not value:
        raise ValueError(f"Missing environment variable: {name}")


def check_env():
    required = {
        "STRAVA_CLIENT_ID": STRAVA_CLIENT_ID,
        "STRAVA_CLIENT_SECRET": STRAVA_CLIENT_SECRET,
        "STRAVA_REFRESH_TOKEN": STRAVA_REFRESH_TOKEN,
        "NOTION_TOKEN": NOTION_TOKEN,
        "NOTION_DATABASE_ID": NOTION_DATABASE_ID,
    }

    for name, value in required.items():
        require_env(name, value)


def notion_headers():
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def title_property(value):
    if not value:
        value = "Strava Activity"

    return {
        "title": [
            {
                "text": {
                    "content": str(value)
                }
            }
        ]
    }


def rich_text_property(value):
    if value is None:
        value = ""

    return {
        "rich_text": [
            {
                "text": {
                    "content": str(value)
                }
            }
        ]
    }


def number_value(value, decimals=2):
    if value is None:
        return None

    return round(float(value), decimals)


def number_property(value, decimals=2):
    value = number_value(value, decimals)
    return {
        "number": value
    }


def select_property(value):
    if not value:
        value = "Activity"

    return {
        "select": {
            "name": str(value)
        }
    }


def date_property(value):
    if not value:
        return {
            "date": None
        }

    return {
        "date": {
            "start": value
        }
    }


def url_property(value):
    return {
        "url": value
    }


def format_pace(activity):
    distance_m = activity.get("distance") or 0
    moving_time_s = activity.get("moving_time") or 0
    sport_type = activity.get("sport_type") or activity.get("type") or ""

    if distance_m <= 0 or moving_time_s <= 0:
        return ""

    distance_km = distance_m / 1000

    if "Run" in sport_type:
        pace_min_per_km = moving_time_s / 60 / distance_km
        minutes = int(pace_min_per_km)
        seconds = int(round((pace_min_per_km - minutes) * 60))

        if seconds == 60:
            minutes += 1
            seconds = 0

        return f"{minutes}:{seconds:02d}/km"

    speed_kmh = distance_km / (moving_time_s / 3600)
    return f"{speed_kmh:.1f} km/h"


# =========================
# Strava
# =========================

def refresh_strava_access_token():
    response = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": STRAVA_CLIENT_ID,
            "client_secret": STRAVA_CLIENT_SECRET,
            "refresh_token": STRAVA_REFRESH_TOKEN,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )

    print("Strava token refresh status:", response.status_code)

    if not response.ok:
        print("Strava token refresh error:")
        print(response.text)
        response.raise_for_status()

    data = response.json()

    access_token = data["access_token"]
    new_refresh_token = data.get("refresh_token")

    if new_refresh_token and new_refresh_token != STRAVA_REFRESH_TOKEN:
        print("Strava returned a new refresh token. Updating .env automatically...")
        set_key(str(ENV_FILE), "STRAVA_REFRESH_TOKEN", new_refresh_token)

    return access_token


def get_all_activities(access_token, per_page=200, max_pages=None):
    all_activities = []
    page = 1

    while True:
        if max_pages is not None and page > max_pages:
            break

        response = requests.get(
            "https://www.strava.com/api/v3/athlete/activities",
            headers={
                "Authorization": f"Bearer {access_token}"
            },
            params={
                "page": page,
                "per_page": per_page
            },
            timeout=30,
        )

        print(f"Strava activities page {page} status:", response.status_code)

        if not response.ok:
            print("Strava activities error:")
            print(response.text)
            response.raise_for_status()

        activities = response.json()

        if not activities:
            break

        all_activities.extend(activities)
        print(f"Fetched page {page}: {len(activities)} activities")

        if len(activities) < per_page:
            break

        page += 1

    return all_activities


# =========================
# Notion
# =========================

def get_notion_database_properties():
    response = requests.get(
        f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}",
        headers=notion_headers(),
        timeout=30,
    )

    print("Notion database status:", response.status_code)

    if not response.ok:
        print("Notion database error:")
        print(response.text)
        response.raise_for_status()

    database = response.json()
    return database.get("properties", {})


def has_property(database_properties, property_name):
    return property_name in database_properties


def add_property_if_exists(properties, database_properties, property_name, value):
    if has_property(database_properties, property_name):
        properties[property_name] = value
    else:
        print(f"Warning: Notion property missing, skipped: {property_name}")


def activity_exists(strava_id):
    response = requests.post(
        f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query",
        headers=notion_headers(),
        json={
            "filter": {
                "property": "Strava ID",
                "rich_text": {
                    "equals": str(strava_id)
                }
            },
            "page_size": 1,
        },
        timeout=30,
    )

    if not response.ok:
        print("Notion query error:")
        print("Status:", response.status_code)
        print(response.text)
        response.raise_for_status()

    result = response.json()
    return len(result.get("results", [])) > 0


def create_notion_activity(activity, database_properties):
    strava_id = str(activity["id"])
    name = activity.get("name") or "Strava Activity"
    sport_type = activity.get("sport_type") or activity.get("type") or "Activity"

    distance_km = (activity.get("distance") or 0) / 1000
    moving_time_min = (activity.get("moving_time") or 0) / 60
    elevation_m = activity.get("total_elevation_gain")
    avg_hr = activity.get("average_heartrate")
    max_hr = activity.get("max_heartrate")
    start_date = activity.get("start_date_local") or activity.get("start_date")

    strava_url = f"https://www.strava.com/activities/{strava_id}"
    pace = format_pace(activity)

    properties = {}

    # Core properties
    add_property_if_exists(
        properties,
        database_properties,
        "Name",
        title_property(name)
    )

    add_property_if_exists(
        properties,
        database_properties,
        "Strava ID",
        rich_text_property(strava_id)
    )

    add_property_if_exists(
        properties,
        database_properties,
        "Date",
        date_property(start_date)
    )

    add_property_if_exists(
        properties,
        database_properties,
        "Type",
        select_property(sport_type)
    )

    # Preferred clean field names
    add_property_if_exists(
        properties,
        database_properties,
        "Distance km",
        number_property(distance_km, 2)
    )

    add_property_if_exists(
        properties,
        database_properties,
        "Moving Time min",
        number_property(moving_time_min, 1)
    )

    # Optional fields
    if elevation_m is not None:
        add_property_if_exists(
            properties,
            database_properties,
            "Elevation m",
            number_property(elevation_m, 1)
        )

    if avg_hr is not None:
        add_property_if_exists(
            properties,
            database_properties,
            "Avg HR",
            number_property(avg_hr, 0)
        )

    if max_hr is not None:
        add_property_if_exists(
            properties,
            database_properties,
            "Max HR",
            number_property(max_hr, 0)
        )

    add_property_if_exists(
        properties,
        database_properties,
        "Pace",
        rich_text_property(pace)
    )

    add_property_if_exists(
        properties,
        database_properties,
        "Strava URL",
        url_property(strava_url)
    )

    add_property_if_exists(
        properties,
        database_properties,
        "Source",
        select_property("Strava")
    )

    add_property_if_exists(
        properties,
        database_properties,
        "Notes",
        rich_text_property("Synced from Strava")
    )

    response = requests.post(
        "https://api.notion.com/v1/pages",
        headers=notion_headers(),
        json={
            "parent": {
                "database_id": NOTION_DATABASE_ID
            },
            "properties": properties,
        },
        timeout=30,
    )

    if not response.ok:
        print("Notion create page error:")
        print("Status:", response.status_code)
        print(response.text)
        response.raise_for_status()


# =========================
# Main
# =========================

def main():
    check_env()

    print("Refreshing Strava access token...")
    access_token = refresh_strava_access_token()

    print("Reading Notion database properties...")
    database_properties = get_notion_database_properties()

    print("Fetching all Strava activities...")
    activities = get_all_activities(
        access_token,
        per_page=PER_PAGE,
        max_pages=MAX_PAGES
    )

    print(f"Found {len(activities)} activities in total.")

    synced = 0
    skipped = 0
    failed = 0

    for index, activity in enumerate(activities, start=1):
        strava_id = activity["id"]
        name = activity.get("name", "Unnamed Activity")

        print()
        print(f"[{index}/{len(activities)}] {name}")

        try:
            if activity_exists(strava_id):
                print(f"Skipped existing: {name}")
                skipped += 1
                continue

            create_notion_activity(activity, database_properties)
            print(f"Synced: {name}")
            synced += 1

        except Exception as error:
            print(f"Failed: {name}")
            print(error)
            failed += 1

    print()
    print("Done.")
    print(f"Synced: {synced}")
    print(f"Skipped existing: {skipped}")
    print(f"Failed: {failed}")


if __name__ == "__main__":
    main()
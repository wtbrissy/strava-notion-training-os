import getpass
import requests
from dotenv import set_key

ENV_FILE = ".env"

client_id = input("Strava Client ID [260460]: ").strip() or "260460"
client_secret = getpass.getpass("Strava Client Secret: ").strip()
code = input("OAuth code from browser URL: ").strip()

response = requests.post(
    "https://www.strava.com/oauth/token",
    data={
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
    },
    timeout=30,
)

print("Status:", response.status_code)

if not response.ok:
    print(response.text)
    response.raise_for_status()

data = response.json()

access_token = data["access_token"]
refresh_token = data["refresh_token"]
scope = data.get("scope")

print("Success.")
print("scope:", scope)
print("refresh_token received and saved to .env")

set_key(ENV_FILE, "STRAVA_CLIENT_ID", client_id)
set_key(ENV_FILE, "STRAVA_CLIENT_SECRET", client_secret)
set_key(ENV_FILE, "STRAVA_REFRESH_TOKEN", refresh_token)

test = requests.get(
    "https://www.strava.com/api/v3/athlete",
    headers={"Authorization": f"Bearer {access_token}"},
    timeout=30,
)

print("Athlete test status:", test.status_code)

if test.ok:
    athlete = test.json()
    print("Connected athlete:", athlete.get("firstname"), athlete.get("lastname"))
else:
    print(test.text)
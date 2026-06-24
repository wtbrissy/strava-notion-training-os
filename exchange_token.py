import getpass
import requests

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

if response.ok:
    data = response.json()
    print("Success.")
    print("scope:", data.get("scope"))
    print("refresh_token:", data.get("refresh_token"))
else:
    print(response.text)
    response.raise_for_status()


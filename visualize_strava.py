import os
from pathlib import Path
import webbrowser

import requests
import pandas as pd
import matplotlib.pyplot as plt
from dotenv import load_dotenv


# =========================
# Settings
# =========================

ENV_FILE = Path(__file__).with_name(".env")
load_dotenv(dotenv_path=ENV_FILE)

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

NOTION_VERSION = "2022-06-28"

OUTPUT_DIR = Path(__file__).with_name("charts")
OUTPUT_DIR.mkdir(exist_ok=True)

HTML_REPORT = Path(__file__).with_name("training_dashboard.html")

# Change this if you want 60 / 90 days
DASHBOARD_DAYS = 60


# =========================
# Notion helpers
# =========================

def notion_headers():
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def require_env(name, value):
    if not value:
        raise ValueError(f"Missing environment variable: {name}")


def get_title(prop):
    items = prop.get("title", [])
    return "".join(item.get("plain_text", "") for item in items)


def get_rich_text(prop):
    items = prop.get("rich_text", [])
    return "".join(item.get("plain_text", "") for item in items)


def get_select(prop):
    value = prop.get("select")
    if not value:
        return None
    return value.get("name")


def get_number(prop):
    return prop.get("number")


def get_date(prop):
    value = prop.get("date")
    if not value:
        return None
    return value.get("start")


def get_url(prop):
    return prop.get("url")


def fetch_all_notion_pages():
    require_env("NOTION_TOKEN", NOTION_TOKEN)
    require_env("NOTION_DATABASE_ID", NOTION_DATABASE_ID)

    pages = []
    cursor = None

    while True:
        payload = {"page_size": 100}

        if cursor:
            payload["start_cursor"] = cursor

        response = requests.post(
            f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query",
            headers=notion_headers(),
            json=payload,
            timeout=30,
        )

        print("Notion query status:", response.status_code)

        if not response.ok:
            print(response.text)
            response.raise_for_status()

        data = response.json()
        pages.extend(data.get("results", []))

        if not data.get("has_more"):
            break

        cursor = data.get("next_cursor")

    return pages


def map_sport_type(value):
    if not value:
        return "Other"

    value = str(value).lower()

    if "run" in value:
        return "Run"

    if "ride" in value or "virtualride" in value:
        return "Ride"

    if "swim" in value:
        return "Swim"

    if "walk" in value:
        return "Walk"

    if "hike" in value:
        return "Hike"

    if "workout" in value or "weight" in value or "gym" in value:
        return "Gym"

    return "Other"


def pages_to_dataframe(pages):
    rows = []

    for page in pages:
        props = page.get("properties", {})

        row = {
            "Name": get_title(props.get("Name", {})),
            "Strava ID": get_rich_text(props.get("Strava ID", {})),
            "Date": get_date(props.get("Date", {})),
            "Type": get_select(props.get("Type", {})),
            "Distance km": get_number(props.get("Distance km", {})),
            "Moving Time min": get_number(props.get("Moving Time min", {})),
            "Elevation m": get_number(props.get("Elevation m", {})),
            "Avg HR": get_number(props.get("Avg HR", {})),
            "Max HR": get_number(props.get("Max HR", {})),
            "Pace": get_rich_text(props.get("Pace", {})),
            "Strava URL": get_url(props.get("Strava URL", {})),
            "Source": get_select(props.get("Source", {})),
        }

        rows.append(row)

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])

    numeric_cols = [
        "Distance km",
        "Moving Time min",
        "Elevation m",
        "Avg HR",
        "Max HR",
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["Sport"] = df["Type"].apply(map_sport_type)

    # Avoid PeriodIndex plotting errors by converting weeks/months to plain strings
    week_start = df["Date"] - pd.to_timedelta(df["Date"].dt.weekday, unit="D")
    df["Week"] = week_start.dt.strftime("%Y-%m-%d")
    df["Month"] = df["Date"].dt.strftime("%Y-%m")

    return df.sort_values("Date")


# =========================
# Chart helpers
# =========================

def save_current_chart(filename):
    path = OUTPUT_DIR / filename
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()
    print("Saved:", path)
    return path


def make_weekly_distance_chart(df):
    weekly = (
        df.pivot_table(
            index="Week",
            columns="Sport",
            values="Distance km",
            aggfunc="sum",
            fill_value=0,
        )
        .sort_index()
    )

    if weekly.empty:
        return None

    weekly.index = weekly.index.astype(str)

    ax = weekly.plot(kind="bar", stacked=True, figsize=(12, 6))
    ax.set_title(f"Weekly training distance - last {DASHBOARD_DAYS} days")
    ax.set_xlabel("Week starting")
    ax.set_ylabel("Distance km")
    ax.legend(title="Sport")

    return save_current_chart("weekly_distance_by_sport.png")


def make_weekly_time_chart(df):
    weekly = (
        df.groupby("Week")["Moving Time min"]
        .sum()
        .sort_index()
    )

    if weekly.empty:
        return None

    weekly.index = weekly.index.astype(str)
    hours = weekly / 60

    ax = hours.plot(kind="line", marker="o", figsize=(12, 6))
    ax.set_title(f"Weekly training time - last {DASHBOARD_DAYS} days")
    ax.set_xlabel("Week starting")
    ax.set_ylabel("Hours")

    return save_current_chart("weekly_training_time.png")


def make_activity_mix_chart(df):
    counts = df["Sport"].value_counts()

    if counts.empty:
        return None

    ax = counts.plot(kind="bar", figsize=(10, 6))
    ax.set_title(f"Activity mix - last {DASHBOARD_DAYS} days")
    ax.set_xlabel("Sport")
    ax.set_ylabel("Activity count")

    return save_current_chart("activity_mix.png")


def make_distance_by_sport_chart(df):
    distance = (
        df.groupby("Sport")["Distance km"]
        .sum()
        .sort_values(ascending=False)
    )

    if distance.empty:
        return None

    ax = distance.plot(kind="bar", figsize=(10, 6))
    ax.set_title(f"Distance by sport - last {DASHBOARD_DAYS} days")
    ax.set_xlabel("Sport")
    ax.set_ylabel("Distance km")

    return save_current_chart("distance_by_sport.png")


def make_run_pace_hr_chart(df):
    runs = df[
        (df["Sport"] == "Run")
        & (df["Distance km"] > 0)
        & (df["Moving Time min"] > 0)
        & (df["Avg HR"].notna())
    ].copy()

    if runs.empty:
        print("Skipped run pace vs HR chart: no run data with Avg HR.")
        return None

    runs["Pace min/km"] = runs["Moving Time min"] / runs["Distance km"]

    runs = runs[
        (runs["Pace min/km"] >= 3)
        & (runs["Pace min/km"] <= 12)
        & (runs["Avg HR"] >= 80)
        & (runs["Avg HR"] <= 220)
    ]

    if runs.empty:
        print("Skipped run pace vs HR chart: no clean run data after filtering.")
        return None

    ax = runs.plot(
        kind="scatter",
        x="Avg HR",
        y="Pace min/km",
        figsize=(10, 6),
    )

    ax.set_title(f"Running pace vs average heart rate - last {DASHBOARD_DAYS} days")
    ax.set_xlabel("Average heart rate")
    ax.set_ylabel("Pace min/km lower is faster")
    ax.invert_yaxis()

    return save_current_chart("run_pace_vs_hr.png")


def make_summary(df):
    if df.empty:
        return {
            "latest_date": "N/A",
            "start_date": "N/A",
            "total_activities": 0,
            "total_distance": 0,
            "total_hours": 0,
            "run_distance": 0,
            "ride_distance": 0,
            "avg_hr": None,
        }

    latest_date = df["Date"].max()
    start_date = df["Date"].min()

    total_activities = len(df)
    total_distance = df["Distance km"].sum()
    total_hours = df["Moving Time min"].sum() / 60
    run_distance = df.loc[df["Sport"] == "Run", "Distance km"].sum()
    ride_distance = df.loc[df["Sport"] == "Ride", "Distance km"].sum()
    avg_hr = df["Avg HR"].dropna().mean()

    return {
        "latest_date": latest_date.strftime("%Y-%m-%d"),
        "start_date": start_date.strftime("%Y-%m-%d"),
        "total_activities": int(total_activities),
        "total_distance": round(float(total_distance), 1),
        "total_hours": round(float(total_hours), 1),
        "run_distance": round(float(run_distance), 1),
        "ride_distance": round(float(ride_distance), 1),
        "avg_hr": round(float(avg_hr), 0) if pd.notna(avg_hr) else None,
    }


def make_html_report(summary, chart_paths):
    chart_html = ""

    for path in chart_paths:
        if path is None:
            continue

        relative_path = path.relative_to(Path(__file__).parent)
        chart_html += f"""
        <section class="card">
            <img src="{relative_path.as_posix()}" alt="{path.stem}">
        </section>
        """

    avg_hr_text = summary["avg_hr"] if summary["avg_hr"] is not None else "N/A"

    html = f"""
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <title>Strava Training Dashboard</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 32px;
            background: #f6f6f6;
            color: #222;
        }}

        h1 {{
            margin-bottom: 4px;
        }}

        .subtitle {{
            color: #666;
            margin-bottom: 24px;
        }}

        .metrics {{
            display: grid;
            grid-template-columns: repeat(3, minmax(160px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}

        .metric {{
            background: white;
            padding: 18px;
            border-radius: 12px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        }}

        .metric .label {{
            color: #666;
            font-size: 13px;
        }}

        .metric .value {{
            font-size: 28px;
            font-weight: bold;
            margin-top: 8px;
        }}

        .card {{
            background: white;
            padding: 18px;
            margin-bottom: 24px;
            border-radius: 12px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        }}

        img {{
            width: 100%;
            height: auto;
            display: block;
        }}
    </style>
</head>
<body>
    <h1>Strava Training Dashboard</h1>
    <div class="subtitle">
        Showing the last {DASHBOARD_DAYS} days from your Notion Strava database.
        Range: {summary["start_date"]} to {summary["latest_date"]}.
    </div>

    <div class="metrics">
        <div class="metric">
            <div class="label">Activities</div>
            <div class="value">{summary["total_activities"]}</div>
        </div>

        <div class="metric">
            <div class="label">Total distance</div>
            <div class="value">{summary["total_distance"]} km</div>
        </div>

        <div class="metric">
            <div class="label">Training time</div>
            <div class="value">{summary["total_hours"]} h</div>
        </div>

        <div class="metric">
            <div class="label">Run distance</div>
            <div class="value">{summary["run_distance"]} km</div>
        </div>

        <div class="metric">
            <div class="label">Ride distance</div>
            <div class="value">{summary["ride_distance"]} km</div>
        </div>

        <div class="metric">
            <div class="label">Average HR</div>
            <div class="value">{avg_hr_text}</div>
        </div>
    </div>

    {chart_html}
</body>
</html>
"""

    HTML_REPORT.write_text(html, encoding="utf-8")
    print("HTML report saved:", HTML_REPORT)

    return HTML_REPORT


# =========================
# Main
# =========================

def main():
    print("Fetching Strava data from Notion...")
    pages = fetch_all_notion_pages()
    print(f"Fetched {len(pages)} Notion rows.")

    df = pages_to_dataframe(pages)

    if df.empty:
        print("No data found.")
        return

    print(f"Loaded {len(df)} total activities.")
    print("Full data range:", df["Date"].min(), "to", df["Date"].max())

    latest_date = df["Date"].max()
    cutoff_date = latest_date - pd.Timedelta(days=DASHBOARD_DAYS)

    chart_df = df[df["Date"] >= cutoff_date].copy()

    print(f"Dashboard range: {cutoff_date.date()} to {latest_date.date()}")
    print(f"Activities in dashboard range: {len(chart_df)}")

    if chart_df.empty:
        print("No activities in dashboard range.")
        return

    summary = make_summary(chart_df)

    chart_paths = [
        make_weekly_distance_chart(chart_df),
        make_weekly_time_chart(chart_df),
        make_activity_mix_chart(chart_df),
        make_distance_by_sport_chart(chart_df),
        make_run_pace_hr_chart(chart_df),
    ]

    report_path = make_html_report(summary, chart_paths)

    webbrowser.open(report_path.as_uri())


if __name__ == "__main__":
    main()
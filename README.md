# Strava to Notion Training OS

A Python-based personal training automation system that syncs Strava activities into Notion and generates a local visual training dashboard.

📖 Medium write-up: [Training in Dad Mode: How I Built a Strava-to-Notion Dashboard with Python](https://medium.com/@winston.liang/training-in-dad-mode-how-i-built-a-strava-to-notion-dashboard-with-python-463ea5a672a1)

## Features

- Sync Strava activities into Notion
- Avoid duplicate records using Strava activity ID
- Automatically refresh Strava tokens
- Generate 30-day training dashboard
- Visualise weekly distance, training time, activity mix, and running pace vs heart rate
- Supports daily automation with Windows Task Scheduler

## Tech Stack

- Python
- Strava API
- Notion API
- pandas
- matplotlib
- Windows Task Scheduler

## Setup

Create a `.env` file based on `.env.example`.

```env
STRAVA_CLIENT_ID=your_strava_client_id
STRAVA_CLIENT_SECRET=your_strava_client_secret
STRAVA_REFRESH_TOKEN=your_strava_refresh_token

NOTION_TOKEN=your_notion_token
NOTION_DATABASE_ID=your_notion_database_id
```

Install packages:

```bash
pip install requests python-dotenv pandas matplotlib
```

Run sync:

```bash
python sync_strava_to_notion.py
```

Generate dashboard:

```bash
python visualize_strava.py
```

## Note

This repository does not include private tokens, logs, charts, or personal activity data.

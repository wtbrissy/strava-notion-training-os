@echo off
setlocal

REM ==============================
REM Strava to Notion GitHub Uploader
REM ==============================

cd /d C:\Users\Winston\Documents\strava-notion-sync

set REPO_NAME=strava-notion-training-os
set VISIBILITY=public

echo.
echo ==============================
echo GitHub Upload: %REPO_NAME%
echo ==============================
echo.

REM Check git
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo Git is not installed or not in PATH.
    echo Install Git first: https://git-scm.com/downloads
    pause
    exit /b 1
)

REM Check GitHub CLI
where gh >nul 2>nul
if %errorlevel% neq 0 (
    echo GitHub CLI is not installed.
    echo Installing GitHub CLI via winget...
    winget install --id GitHub.cli -e
    echo.
    echo Please close this window, reopen PowerShell, run:
    echo gh auth login
    echo Then run this .bat again.
    pause
    exit /b 1
)

REM Check GitHub auth
gh auth status >nul 2>nul
if %errorlevel% neq 0 (
    echo You are not logged into GitHub CLI.
    echo Please complete GitHub login now.
    gh auth login
)

REM Create safe .gitignore
echo Creating .gitignore...

(
echo .env
echo .venv/
echo __pycache__/
echo *.pyc
echo logs/
echo charts/
echo training_dashboard.html
echo .DS_Store
echo Thumbs.db
) > .gitignore

REM Create .env.example
echo Creating .env.example...

(
echo STRAVA_CLIENT_ID=your_strava_client_id
echo STRAVA_CLIENT_SECRET=your_strava_client_secret
echo STRAVA_REFRESH_TOKEN=your_strava_refresh_token
echo.
echo NOTION_TOKEN=your_notion_token
echo NOTION_DATABASE_ID=your_notion_database_id
) > .env.example

REM Safety: remove secrets from git cache if accidentally tracked
git rm --cached .env >nul 2>nul
git rm -r --cached .venv >nul 2>nul
git rm -r --cached logs >nul 2>nul
git rm -r --cached charts >nul 2>nul
git rm --cached training_dashboard.html >nul 2>nul

REM Create README placeholder if missing
if not exist README.md (
    echo Creating README.md...
    (
    echo # Strava to Notion Training OS
    echo.
    echo A Python-based personal training automation system that syncs Strava activities into Notion and generates a local visual training dashboard.
    echo.
    echo ## Features
    echo.
    echo - Sync Strava activities into Notion
    echo - Avoid duplicate records using Strava activity ID
    echo - Automatically refresh Strava tokens
    echo - Generate 30-day training dashboard
    echo - Visualise weekly distance, training time, activity mix, and running pace vs heart rate
    echo - Supports daily automation with Windows Task Scheduler
    echo.
    echo ## Tech Stack
    echo.
    echo - Python
    echo - Strava API
    echo - Notion API
    echo - pandas
    echo - matplotlib
    echo - Windows Task Scheduler
    echo.
    echo ## Setup
    echo.
    echo Create a `.env` file based on `.env.example`.
    echo.
    echo ```env
    echo STRAVA_CLIENT_ID=your_strava_client_id
    echo STRAVA_CLIENT_SECRET=your_strava_client_secret
    echo STRAVA_REFRESH_TOKEN=your_strava_refresh_token
    echo.
    echo NOTION_TOKEN=your_notion_token
    echo NOTION_DATABASE_ID=your_notion_database_id
    echo ```
    echo.
    echo Install packages:
    echo.
    echo ```bash
    echo pip install requests python-dotenv pandas matplotlib
    echo ```
    echo.
    echo Run sync:
    echo.
    echo ```bash
    echo python sync_strava_to_notion.py
    echo ```
    echo.
    echo Generate dashboard:
    echo.
    echo ```bash
    echo python visualize_strava.py
    echo ```
    echo.
    echo ## Note
    echo.
    echo This repository does not include private tokens, logs, charts, or personal activity data.
    ) > README.md
)

REM Initialize git if needed
if not exist .git (
    echo Initializing git repository...
    git init
)

REM Add files
git add .

REM Commit
git commit -m "Initial Strava to Notion Training OS showcase"

REM Create GitHub repo if it does not exist
echo Creating GitHub repository...
gh repo create %REPO_NAME% --%VISIBILITY% --source=. --remote=origin --push

if %errorlevel% neq 0 (
    echo.
    echo Repo may already exist. Trying normal push...
    git branch -M main
    git remote remove origin >nul 2>nul
    gh repo view %REPO_NAME% >nul 2>nul
    if %errorlevel% neq 0 (
        echo Could not find or create repo. Please check GitHub CLI login.
        pause
        exit /b 1
    )
    git remote add origin https://github.com/%USERNAME%/%REPO_NAME%.git
    git push -u origin main
)

echo.
echo ==============================
echo Upload complete.
echo ==============================
echo Repo name: %REPO_NAME%
echo Visibility: %VISIBILITY%
echo.
pause
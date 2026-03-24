# Phoenix Rankings (GitHub Pages)

This is a static website that displays:

- Ranking (by total score)
- Count of 1st / 2nd / 3rd / 4th places per player
- Year filter (multi-select)

The site reads a static JSON file at `public/data.json` so it can be deployed to GitHub Pages.

## Update Data

From `match_result/`:

```powershell
$env:DB_NAME="postgres"
$env:DB_USER="postgres"
$env:DB_PASSWORD="5abtr9ah"
.\venv\Scripts\python export_site_data_from_db.py
```

This regenerates [data.json](file:///c:/Users/CH%20Tam/Documents/trae_projects/match_result/site/public/data.json) directly from Postgres (includes Regular / Semi-Final / Final).

## Local Dev

```powershell
cd match_result/site
npm install
npm run dev
```

## Build

```powershell
cd match_result/site
npm run build
```

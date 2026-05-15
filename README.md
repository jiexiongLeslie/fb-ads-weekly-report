# Datenanalyse-Dashboard

Local Flask app for syncing Facebook Ads data and viewing the analytics dashboard.

## Structure

```text
trea_al/
├─ datenanalyse-dashboard.html Frontend dashboard page
├─ backend/
│  ├─ server.py                Flask app and API server
│  └─ test_api.py              API smoke test
├─ fb_ads_data.json            Synced ad data, ignored by git
├─ fb_audience_data.json       Audience cache, ignored by git
├─ fb_audience_cache/          Daily audience cache, ignored by git
├─ start.bat                   Start in background and open browser
├─ start-background.bat        Start service in background only
└─ install-auto-start.bat      Register Windows logon auto start
```

## Run

Double-click `start.bat`, or run:

```powershell
.\start.bat
```

The app runs at:

```text
http://localhost:5003
```

## Auto Start

Run `install-auto-start.bat` once. It creates Windows Scheduled Tasks named
`Datenanalyse-Dashboard` and `Datenanalyse-Dashboard Watchdog`, starts the
service on user logon, and checks every 5 minutes that it is still running.

Logs are written to `logs/server.log`.

## Configuration

Facebook credentials are read from user environment variables:

```text
FB_APP_ID
FB_APP_SECRET
FB_ACCESS_TOKEN
FB_BUSINESS_ID
FB_REPORT_PORT
```

`FB_REPORT_PORT` is optional and defaults to `5003`.

## API

| Endpoint | Method | Description |
| --- | --- | --- |
| `/api/sync` | POST | Sync ad data |
| `/api/sync/progress` | GET | Sync progress |
| `/api/data` | GET | Read saved data |
| `/api/config` | GET/POST | Read or save UI config |
| `/api/audience/fetch` | POST | Fetch audience breakdowns |
| `/api/audience/customer-type` | POST | Fetch customer type data |
| `/api/accounts` | GET | List configured ad accounts |
| `/api/token-status` | GET | Check token status |

## Smoke Test

Start the service first, then run:

```powershell
py backend\test_api.py
```

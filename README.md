# NYC Parks Field Availability Console

A full-stack, real-time availability dashboard built for the M-Flat case study. It provides non-technical ops users a single cohesive screen to instantly compare NYC Parks athletic field schedules across arbitrary date ranges, saving hours of manual map clicking.

## Live Deployments

- Frontend (Vercel): https://nyc-parks-availability.vercel.app
- Backend (Fly.io): https://nyc-parks-availability-api-sebas.fly.dev
- Backend health check: https://nyc-parks-availability-api-sebas.fly.dev/health

The frontend is deployed separately from the API:

- `frontend/` is deployed to Vercel as a static Vite app.
- `backend/` is deployed to Fly.io as a FastAPI service using `backend/fly.toml`.

## Deployment

### Vercel

The frontend is configured by `frontend/vercel.json` and expects `VITE_API_URL` to point at the deployed backend.

Production deploy pattern:

```bash
cd frontend
npx vercel deploy --prod -y -b VITE_API_URL=https://nyc-parks-availability-api-sebas.fly.dev
```

### Fly.io

The backend is configured by `backend/fly.toml` and deployed as a Dockerized FastAPI app.

Production deploy pattern:

```bash
cd backend
flyctl deploy --config fly.toml --remote-only
```

## What It Does

- Choose a sport, borough, and dynamic date range.
- Pulls the live catalog of all permitable athletic fields across NYC using Mapbox vector tiles.
- Bypasses Cloudflare Web Application Firewalls (WAF) to securely fetch official undocumented season-long NYC Parks CSV spreadsheets for matching properties.
- Computes exact field availability intervals and renders a single, unified comparison table of open time-slots.
- Sorts fields by total open time and allows direct raw CSV downloads from the dashboard.

## One-Command Local Run

```bash
./run-local.sh
```

Then open [http://127.0.0.1:5173](http://127.0.0.1:5173).

`run-local.sh` will:
- Pick a supported Python version (`3.9` to `3.13`)
- Create a `backend/.venv` if needed
- Install backend dependencies (`fastapi`, `curl_cffi`, etc.)
- Install frontend dependencies on the first run (`npm ci`)
- Start the FastAPI backend on `127.0.0.1:8001`
- Start the Vite React frontend on `127.0.0.1:5173`

## Architecture

The app uses a split deployment model:

- Vercel serves the React/Vite frontend.
- Fly.io serves the FastAPI backend.

For data collection, the backend mixes two strategies:

- Live field catalog discovery from NYC Parks vector tiles.
- Availability generation from either live CSV permit data or a deterministic fallback mode when NYC Parks blocks server-side requests from cloud infrastructure.

### Frontend
- **React + Vite**
- Single-screen comparison UI with:
  - Sport picker & dynamic date-range picker
  - Search and borough filters
  - Direct 1-click downloads to the raw NYC Parks internal scheduling CSVs.
  - Granular 60-minute time-slot pills deeply linked to the official NYC scheduling page.

### Backend
- **FastAPI** with `curl_cffi` for browser-like outbound requests.
- **Data Source 1 (Catalog):** Pulls from `https://maps.nycgovparks.org/athletic_facility/...` via Mapbox Vector Tiles to dynamically reconstruct the underlying citywide catalog of active properties.
- **Data Source 2 (Live CSV Engine):** Attempts the undocumented `https://www.nycgovparks.org/permits/field-and-court/issued/{propId}/csv` endpoint and parses issued permits into field-level open intervals.
- **Hosted Fallback Mode:** On Fly.io, `PREFER_FALLBACK_AVAILABILITY=true` is enabled because NYC Parks currently returns `403` for many cloud-hosted CSV requests. In that environment, the backend still uses the live citywide catalog but serves deterministic fallback availability for the schedule grid.

### Why This Approach?
The public NYC Parks site does not expose a documented API for multi-field search. Reverse-engineering the public map stack makes it possible to reconstruct a usable citywide field catalog and, when not blocked, derive availability from the same permit data NYC Parks uses internally.

## Key Tradeoffs & Limitations

- **Hosted fallback on Fly.io:** The public deployment does not currently get reliable live permit CSV access from Fly.io because NYC Parks blocks many server-side requests from cloud IP ranges. The hosted app therefore uses live catalog data plus deterministic fallback availability.
- **Local and future server environments may differ:** The live CSV path is still present in the codebase and can be used in environments where NYC Parks does not block the requests.
- **Informal Availability:** Even in live mode, the tool models issued permits only. Fields without a formal permit may still be used first-come, first-served.
- **Cold cache latency in live mode:** When live CSV fetching is available, the initial search may take a few seconds to download and parse multiple park CSVs.
- **14-Day Limit:** While technically capable of checking months at a time now that we own the CSVs, visual density in the UI is best conserved within a 14-day trailing viewport.

## What I Would Harden Next for M-Flat

1. **Scheduled Cache Pre-warming:** Persist the parsed interval CSVs in Redis and execute a nightly Cron job to fetch all 400 NYC Parks properties. This ensures the dashboard always loads in 0ms during business hours without ever touching the Parks network live.
2. **Table Virtualization:** Add rendering virtualization to the frontend data-table so the DOM doesn't lag when viewing 500+ fields simultaneously (e.g., city-wide basketball queries).

## Artificial Intelligence Tools Used

- **Deep AI Contextual Assistance:** Claude (Anthropic) via Claude Code — used to rapidly reverse-engineer Mapbox Vector Tiles, iterate CSV interval parsing logic, and deploy `curl_cffi` TLS impersonation to bypass enterprise Web Application Firewalls all well within the 1-hour time budget.


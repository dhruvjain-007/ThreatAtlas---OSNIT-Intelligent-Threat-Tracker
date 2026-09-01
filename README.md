# ThreatAtlas — OSINT Intelligent Threat Tracker

A defensive OSINT intelligence monitoring platform that collects publicly available information, processes unstructured reports via NLP (spaCy NER + geocoding), scores threat/credibility, clusters related events, and visualises them on an interactive 3D CesiumJS globe — with live WebSocket feeds and temporal playback.

---

## Architecture

| Layer | Technology |
|---|---|
| **Backend API** | FastAPI (Python 3.10+), APScheduler, WebSockets |
| **NLP / AI** | spaCy `en_core_web_lg`, geopy Nominatim geocoder |
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS v4, CesiumJS |
| **Database** | MongoDB 7 (Geospatial 2dsphere indexes) |
| **Cache / PubSub** | Redis 7 |
| **Infrastructure** | Docker Compose |

---

## Prerequisites

Before you start, ensure the following are installed and available in your PATH:

| Tool | Minimum Version | Download |
|---|---|---|
| **Docker Desktop** | 4.x | https://www.docker.com/products/docker-desktop |
| **Python** | 3.10+ | https://www.python.org/downloads/ |
| **Node.js** | 20+ | https://nodejs.org/ |
| **Git** | any | https://git-scm.com/ |

> **Windows note:** All commands below are for **PowerShell**. Open PowerShell as a regular user (no Administrator required).

---

## Quick Start — Step by Step

### Step 1 — Start Infrastructure (MongoDB + Redis)

Make sure Docker Desktop is running, then spin up the database and cache containers in the background:

```powershell
docker compose -f infrastructure/docker-compose.yml up -d
```

Verify containers are healthy:

```powershell
docker compose -f infrastructure/docker-compose.yml ps
```

Both `threat_atlas_mongodb` (port **27017**) and `threat_atlas_redis` (port **6379**) should show `running`.

---

### Step 2 — Set Up and Start the Backend

Open a **new PowerShell terminal** in the project root.

#### 2a. Create a Python virtual environment

```powershell
cd backend
python -m venv venv
```

#### 2b. Activate the virtual environment

```powershell
.\venv\Scripts\Activate.ps1
```

> If you see an execution policy error, run:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

#### 2c. Install all Python dependencies

```powershell
pip install -r requirements.txt
```

#### 2d. Download the spaCy language model (one-time, ~750 MB)

```powershell
python -m spacy download en_core_web_lg
```

> If disk space is limited, use `en_core_web_sm` instead and update the model name in `app/nlp/service.py`.

#### 2e. Configure environment variables (optional)

The app ships with sensible defaults pointing to `localhost`. To customise, copy the example file:

```powershell
Copy-Item .env.example .env
```

Edit `.env` as needed. The defaults are:

```env
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=threat_atlas
REDIS_URL=redis://localhost:6379/0
```

#### 2f. Start the backend server

```powershell
python -m uvicorn main:app --reload --port 8000
```

You should see output like:

```
INFO  | Starting OSINT Threat Intelligence Platform in development mode...
INFO  | MongoDB connection established to database: threat_atlas
INFO  | APScheduler started successfully.
INFO  | Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

> **Redis not running?** The backend logs a notice and continues using in-memory WebSocket broadcasting. All API endpoints remain fully functional.

| Endpoint | URL |
|---|---|
| **Health Check** | http://localhost:8000/health |
| **Swagger API Docs** | http://localhost:8000/docs |
| **Events API** | http://localhost:8000/api/v1/events |
| **WebSocket** | ws://localhost:8000/api/v1/ws/events |

---

### Step 3 — Set Up and Start the Frontend

Open a **second PowerShell terminal** in the project root.

```powershell
cd frontend
npm install
npm run dev
```

You should see:

```
  VITE v8.x  ready in XXX ms
  ➜  Local:   http://localhost:3000/
```

| Interface | URL |
|---|---|
| **Frontend Dashboard** | http://localhost:3000 |
| **API Proxy** | Auto-proxied to `http://localhost:8000` |

---

## Workflow & Features

1. **Ingest OSINT Feeds** — The backend scheduler automatically polls configured RSS/OSINT feeds every 15 minutes. Trigger manually via Swagger at `POST /api/v1/intelligence/ingest`.
2. **Process Intelligence** — Click **"Process Pending OSINT"** in the dashboard header to run text cleaning → spaCy NER → geocoding → threat scoring → event clustering.
3. **Explore the 3D Globe** — Filter events by threat level (`High`, `Medium`, `Low`), minimum score, country, and keyword. Click any globe marker to open the intelligence detail drawer.
4. **Temporal Playback** — Use the timeline slider at the bottom of the globe to scrub through historical events chronologically.
5. **Export** — Download filtered events as a **PDF intelligence brief** or a **STIX 2.1 bundle** via the sidebar export buttons.
6. **Live WebSocket Feed** — The top toast banner shows real-time event updates as the scheduler processes new intelligence.

---

## Running Tests

Backend unit and integration tests:

```powershell
cd backend
pytest
```

Frontend production build validation:

```powershell
cd frontend
npm run build
```

TypeScript type-check only (no build output):

```powershell
cd frontend
npx tsc --noEmit
```

---

## Troubleshooting

### Redis connection warning on startup

```
Redis Pub/Sub listener notice: ... Continuing with in-memory broadcasting.
```

**This is non-fatal.** The platform works fully without Redis. To fix it, start Docker containers:

```powershell
docker compose -f infrastructure/docker-compose.yml up -d
```

---

### MongoDB connection error — `ServerSelectionTimeoutError`

```powershell
docker compose -f infrastructure/docker-compose.yml up -d
docker compose -f infrastructure/docker-compose.yml ps
```

---

### Missing Python package — `ModuleNotFoundError`

```powershell
# Activate venv first, then:
pip install -r requirements.txt
```

For spaCy model specifically:

```powershell
python -m spacy download en_core_web_lg
```

---

### Frontend cannot reach backend

- Confirm the backend is running on **port 8000**.
- The Vite dev server (`npm run dev`) automatically proxies all `/api` calls to `http://localhost:8000` — no extra configuration needed.
- Check the backend terminal for startup errors.

---

### PowerShell venv activation blocked

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## Project Structure

```
ThreatAtlas/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI routers & endpoints (events, auth, webhooks, ws)
│   │   ├── core/           # Config, logging, Redis pub/sub
│   │   ├── db/             # MongoDB session & repositories
│   │   ├── ingestion/      # RSS/OSINT feed parsers
│   │   ├── intelligence/   # Threat scoring, clustering, PDF/STIX export
│   │   ├── nlp/            # spaCy NER, geopy geocoder
│   │   ├── schemas/        # Pydantic request/response models
│   │   └── websockets/     # WebSocket connection manager
│   ├── main.py             # FastAPI app + APScheduler lifespan
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── api/            # Axios HTTP client + WebSocket service
│   │   ├── components/     # CesiumJS globe, FilterPanel, EventDetailDrawer, PlaybackSlider
│   │   └── types/          # TypeScript interfaces
│   └── package.json
└── infrastructure/
    └── docker-compose.yml  # MongoDB 7 + Redis 7-alpine containers
```

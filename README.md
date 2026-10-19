# NLFS — Nikita Learn Spanish (prototype)

NLFS is a website I'm building for myself to learn Spanish, using AI tools such as Claude Code and Google Stitch.

Design specs and implementation plans live in `docs/`.

```
Browser ──► Next.js server (frontend/, :3000) ──► FastAPI (backend/, :8000) ──► SQLite (backend/words.db)
```

Pages are server-rendered: Next.js fetches from FastAPI on the server; writes go through
Server Actions (`frontend/src/app/actions.ts`). The browser never talks to FastAPI directly.

## Run

```powershell
python start.py              # starts both servers, opens the browser; Ctrl+C stops both
python start.py --no-browser
```

`start.py` also creates the backend venv / runs `npm install` on first run if they are missing.

Or manually, in two terminals:

```powershell
# 1) backend — creates and seeds words.db on first start
cd backend
.venv\Scripts\python run.py

# 2) frontend
cd frontend
npm run dev
```

Open **http://localhost:3000** (use `localhost`, not `127.0.0.1` — the Next.js dev server only serves its scripts to `localhost`).
API docs: http://127.0.0.1:8000/docs

First-time setup on a new machine:
`cd backend; python -m venv .venv; .venv\Scripts\pip install -r requirements.txt` and `cd frontend; npm install`.

## Tests

```powershell
cd backend
.venv\Scripts\python -m pytest
```

## Reset data
Stop the backend and delete `backend/words.db`; it is re-seeded from `backend/app/seed.py` on next start.

## Not built yet
Material ingestion (`POST /api/theory/ingest` returns 501), translation/matching quizzes, stats graphs, a single launch script.

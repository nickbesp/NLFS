# Session Log — NLFS Prototype

**Date:** 2026-10-13
**Participants:** Nikita + Claude Code (Claude Opus 5.5)
**Goal:** Build a first working skeleton / proof of concept of the NLFS Spanish learning website.

---

## 1. What we talked about

### Starting point
Nikita asked to start building "the website" as a simple prototype, with questions before implementation.
The workspace already had a full project plan at `research/nlfs-plan.md` (Next.js frontend, FastAPI
backend, SQLite database, CEFR levels, SRS flashcards, quizzes, history). The `Nikita_Learn_Fucking_Spanish/`
folder only contained `Materials/` — no code yet.

### Decisions (question by question)

| # | Question | Options discussed | Decision |
|---|---|---|---|
| 1 | Which website? | NLFS vs. something else | **NLFS** |
| 2 | How deep should the skeleton go? | A) frontend only with fake data · B) thin end-to-end slice (frontend → backend → SQLite) · C) backend only | **B — thin end-to-end slice** |
| 3 | How interactive are flashcards & quizzes? | A) basic interaction (flip + rate cards, 5-question multiple-choice quiz that saves results) · B) placeholders only · C) full mechanics (SM-2 + 3 quiz types) | **A — basic interaction** |
| 4 | Where does sample data come from? | A) hand-written seed file · B) excerpts from the `Materials/DeLe_B2` OCR files | **A — hand-written seed** |
| 5 | How does the frontend get data from the backend? | 1) browser fetches via a Next.js `/api` proxy · 2) browser calls FastAPI directly (CORS) · 3) Next.js server fetches data before sending the page | **3 — server-side rendering** |

### Option 1 vs. option 3 (explained during the session)
- **Option 1:** the page arrives empty, shows "Loading…", then JavaScript in the browser fetches the data
  through a proxy. Simple React, every API call visible in DevTools.
- **Option 3:** the Next.js server calls FastAPI first and sends a finished page. No loading flash, but
  data loading is invisible in the browser, and interactive parts still need small browser-side components.
- Claude recommended option 1 (simpler for a local single-user app); **Nikita chose option 3.**

### Agreed scope
- In: all pages from the plan, real data from SQLite, SM-2 flashcard scheduling, multiple-choice quiz
  graded on the backend, topic completion, quiz history, minimal black/white/gray theme.
- Out (for later): material ingestion pipeline, translation/matching quiz types, stats graphs, auth, deployment.
- Git was offered but not requested, so **no git repository was set up.**

---

## 2. What was implemented

### Spec
- `research/nlfs-prototype-spec.md` — short spec of the prototype (scope, architecture, API, testing).
  The separate step-by-step implementation plan was skipped because Nikita asked to go straight to implementation.

### Architecture
```
Browser ──► Next.js server (frontend/, :3000) ──► FastAPI (backend/, :8000) ──► SQLite (backend/words.db)
```
- Pages are React Server Components: the Next.js server fetches from FastAPI on every request.
- Writes (quiz submit, card rating, "mark as read") go through Next.js **Server Actions**
  (`frontend/src/app/actions.ts`). The browser never talks to FastAPI directly.

### Backend — `backend/` (Python 3.11, FastAPI, SQLAlchemy, SQLite)
| File | Purpose |
|---|---|
| `app/database.py` | SQLite engine/session; DB path overridable (used by tests) |
| `app/models.py` | The 4 tables from the plan: `theory_topics`, `flashcards`, `srs_state`, `quiz_history` |
| `app/schemas.py` | Pydantic request/response models |
| `app/crud.py` | Database logic: topics, cards, due cards, reviews, quiz generation & grading, history, stats |
| `app/srs.py` | Real SuperMemo **SM-2** algorithm |
| `app/seed.py` | 5 hand-written topics (A1: Ser vs Estar, Artículos y género, Presente regular; B1: Presente de subjuntivo, Por vs Para), 6 cards each; seeded automatically into an empty DB |
| `app/ingest.py` | Stub — ingestion not implemented yet (endpoint returns 501) |
| `app/main.py` | FastAPI routes (see below) |
| `run.py` | Starts the backend on `127.0.0.1:8000` with auto-reload |
| `requirements.txt` | Pinned dependencies |
| `tests/` | 19 pytest tests (SM-2 + full API flow on a temporary DB) |

**API endpoints:** `GET /api/stats`*, `GET /api/theory/topics?level=`, `GET /api/theory/topics/{id}`,
`POST /api/theory/topics/{id}/complete`, `POST /api/theory/ingest` (501), `GET/POST /api/words`,
`DELETE /api/words/{id}`, `GET /api/srs/review`, `POST /api/srs/review/{id}`, `GET /api/quiz/generate`,
`POST /api/quiz/submit`, `GET /api/quiz/history`*.
(* = added beyond the original plan, needed for the dashboard and history page.)
Quiz answers are never sent to the browser; grading happens on the backend.

### Frontend — `frontend/` (Next.js 16, React 19, TypeScript, plain CSS)
| Route / file | What it shows |
|---|---|
| `/` | Dashboard: topics completed, cards due, deck size, quizzes taken |
| `/theory` | Level picker A1–C1 with completion counts |
| `/theory/[level]` | Topic roadmap for the level, completed badges |
| `/theory/[level]/[topicId]` | Lesson (Markdown), vocabulary table, "Start practice", "Mark as read" |
| `/quizzes` | Topic picker; `?topic=ID` runs a 5-question multiple-choice quiz |
| `/flashcards` | Review of due cards: flip, rate 0–5, rescheduled with SM-2 |
| `/history` | Past quizzes with scores |
| `src/lib/api.ts` | Server-only client for FastAPI |
| `src/app/actions.ts` | Server Actions for all writes |
| `src/components/QuizRunner.tsx`, `FlashcardReview.tsx` | The two interactive (client) components |
| `error.tsx`, `not-found.tsx` | "Backend unreachable" message and 404 page |
| `src/styles/globals.css` | Minimal theme, with automatic dark mode |

### Launcher — `start.py`
Added at Nikita's request after the prototype was working: one command (`python start.py`) runs both servers
in one terminal with `[backend]` / `[frontend]` prefixed output, waits until both respond, opens the browser,
and stops both on Ctrl+C or if either one crashes. Sets up the venv / `npm install` on first run if missing.

### Docs
- `README.md` — how to run, test and reset data.
- `SESSION_LOG.md` — this file.

---

## 3. Verification

- **Backend tests:** 19/19 passing (`cd backend; .venv\Scripts\python -m pytest`).
- **Frontend build:** `next build` passes type checking; all data pages render on request.
- **End-to-end in a real browser** (headless Edge via Playwright, run from a temp folder, not part of the project):
  level → topic → quiz (5/5) → topic marked completed → "mark as read" on another topic →
  3 flashcards reviewed (due count dropped 27 → 24) → history and dashboard updated. No browser errors.
- **Persistence:** data survived a backend restart.
- **Launcher:** started both servers, served pages, and shut everything down (ports freed) when one server was killed.
  Ctrl+C itself could not be pressed from Claude's side — worth confirming on first use.

## 4. Problems found and fixed during the session

1. **Build tried to pre-render pages** at build time while the backend was off → fixed by marking all
   API-backed pages as request-time (`connection()` in `src/lib/api.ts`).
2. **Buttons did nothing in the first browser test** → the Next.js dev server only serves its scripts to
   `localhost`, and the test used `127.0.0.1`. Not an app bug; documented in the README: **always open
   `http://localhost:3000`**.
3. **Launcher output crash** → server output contains characters (Cyrillic path "Учеба", `▲`, `✓`) that the
   Windows code page can't print, which killed the output thread (and could eventually freeze a server).
   Fixed by replacing unprintable characters instead of crashing.

## 5. Open items / next steps

- Material ingestion pipeline (Phase 1 of `research/nlfs-plan.md`) — turn `Materials/` into topics and cards.
- Translation and matching quiz types.
- Stats/graphs on the dashboard (streaks, level completion %).
- Optionally: set up git (exclude the large `Materials/` PDFs and `backend/words.db`).

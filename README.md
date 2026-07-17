# OLC Talent Matching POC

Explainable talent matching for live productions — features **F01–F20**, plus executive reports and StageLync discovery.

## Stack

- **Backend:** FastAPI + SQLAlchemy
- **Database:** **local SQLite** (`backend/olc.db`) — no Docker
- **Vectors:** OpenAI embeddings stored as JSON on each talent (in-process cosine search)
- **Frontend:** Next.js 15 + TypeScript + Tailwind
- **AI:** OpenAI only (`text-embedding-3-small` + `gpt-4o-mini`)

## Quick start

### 1. Backend

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
# Ensure backend/.env has OPENAI_API_KEY=sk-...
uvicorn app.main:app --reload --port 8000
```

First start seeds data + OpenAI embeddings into `olc.db`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:3000

### 3. Tests

```bash
cd backend
.\.venv\Scripts\python -m pytest tests -v
```

(Tests use a temp SQLite DB and skip embeddings.)

## Demo: Executive Reports

1. Open the **Reports** tab.
2. Set period start/end (default covers 2026).
3. Click **Generate pack** — KPI cards + gate-fail chart appear.
4. Download **PDF** or **Excel** from the same pack.

API: `POST /api/reports/executive` with `{ "period_start": "2026-01-01", "period_end": "2026-12-31" }`.

## Demo: StageLync → OLC

1. Open the **StageLync** tab.
2. Click **Sync fixture** (loads `data/stagelync_people.json`).
3. Use **Discover** with a query (e.g. `elite aerial UAE`).
4. Click **Import to OLC** on a person — creates a `TAL-SL-*` talent + link.
5. Click **Open Match** and run a match; shortlist StageLync export prefers linked IDs.

API: `POST /api/stagelync/sync` → `GET /api/stagelync/discover?q=` → `POST /api/stagelync/import/{id}`.

## Notes

| Concern | Choice |
|--------|--------|
| Primary store | Local SQLite file |
| Semantic search | OpenAI embed + cosine over stored vectors |
| Copilot | OpenAI chat grounded on match results |
| Docker | Not required |
| StageLync | Local fixture only (no live API/OAuth) |
| Reports | On-demand PDF/Excel packs (no email cron) |

Optional later: set `DATABASE_URL=postgresql+psycopg://...` for Postgres + pgvector.

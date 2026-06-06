# Hintro Meeting Intelligence Service

A production-minded service that turns meeting transcripts into **grounded** AI insights, tracks action items, detects overdue work, and delivers reminders through real third-party integrations. Every AI insight is mechanically verified against the transcript, so the system does not surface hallucinated citations.

- **Backend:** FastAPI (Python 3.12), SQLAlchemy 2.0 async, Alembic, PostgreSQL + pgvector, Redis
- **Frontend:** Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4
- **AI:** Google Gemini (primary) with an automatic Groq fallback, plus a deterministic grounding verifier
- **Integrations:** Telegram Bot API (two-way) and Discord webhook
- **Scheduler:** GitHub Actions cron calling a protected job endpoint

> Live URLs and the public Swagger link are listed at the top of the repository description and in `/api/evaluation`.

---

## Table of contents

- [Features](#features)
- [Architecture](#architecture)
- [Quick start (Docker)](#quick-start-docker)
- [Local development (manual)](#local-development-manual)
- [Environment variables](#environment-variables)
- [API usage examples](#api-usage-examples)
- [Deployment](#deployment)
- [Scheduled reminders](#scheduled-reminders)
- [Testing](#testing)
- [Project structure](#project-structure)
- [Further docs](#further-docs)

---

## Features

**Core (assignment requirements)**

- JWT authentication for all protected APIs
- Meeting management: create with transcript, get by id, list with pagination and filtering
- AI analysis endpoint producing summary, decisions, follow-ups, and action items
- Grounding and citation enforcement: every insight cites transcript segments, verified deterministically
- Action item management with status tracking (`PENDING`, `IN_PROGRESS`, `COMPLETED`) and filtering
- Overdue detection (`status != COMPLETED AND dueDate < now`)
- Scheduled reminder job that records reminder history
- One+ real third-party integration actively used by the reminder workflow
- Unified API response envelope, request trace IDs, structured logging, validation, global error handling
- Documented database design, public OpenAPI/Swagger, public deployment, `/health` and `/api/evaluation`

**Standout additions**

- **Verifiable citation engine + grounding score:** hallucinated or unsupported citations are dropped before persistence; each insight carries a confidence score.
- **Resilient LLM layer:** Gemini with automatic Groq fallback so the demo survives provider outages and quota limits.
- **Two integrations, two-way Telegram:** mark an action item complete straight from the reminder message.
- **Live streaming analysis:** Server-Sent Events stream progress; the UI shows live stages.
- **Interactive transcript:** clicking a citation highlights and scrolls to the exact source segment.
- **Semantic search:** natural-language search across all meetings using pgvector embeddings (keyword fallback).
- **Analytics dashboard:** KPIs, status breakdown, workload by assignee, 14-day activity, average grounding score.
- **Full DevOps:** Docker, docker-compose, GitHub Actions CI + cron, Redis caching and rate limiting, unit + integration tests.

---

## Architecture

```
hintro/
  backend/          FastAPI service (the major codebase)
    app/
      core/         config, logging, security, errors, envelope, middleware, redis, deps
      db/           async engine + session, declarative base
      models.py     SQLAlchemy ORM (User, Meeting, TranscriptSegment, Insight, ActionItem, Citation, ReminderLog)
      schemas/      Pydantic v2 request/response models (camelCase contract)
      services/     business logic: llm/, grounding, embeddings, meetings, analysis, action_items, reminders, integrations/, search, analytics
      api/routes/   thin HTTP routers
    alembic/        migrations
    tests/          pytest unit + integration
  frontend/         Next.js premium dashboard
  .github/workflows ci.yml, reminders.yml (cron)
  docker-compose.yml
  render.yaml       backend blueprint
```

Request lifecycle: `RequestContextMiddleware` assigns a trace id, logs the request, and wraps successful JSON in `{ traceId, success, data }`. Errors flow through global handlers into `{ traceId, success: false, error }`. `/health` and `/api/evaluation` are returned raw to match their fixed contracts.

See [DECISIONS.md](./DECISIONS.md) for the rationale behind each major choice.

---

## Quick start (Docker)

Requires Docker.

```bash
git clone <repo-url> hintro && cd hintro
cp backend/.env.example backend/.env   # then add GEMINI_API_KEY / GROQ_API_KEY
docker compose up -d db redis           # Postgres (pgvector) on 5433, Redis on 6379
docker compose up --build api           # API on http://localhost:8000
```

Then seed demo data and open the docs:

```bash
docker compose exec api uv run python -m scripts.seed
open http://localhost:8000/api/docs
```

Run the frontend:

```bash
cd frontend
cp .env.example .env.local              # NEXT_PUBLIC_API_URL=http://localhost:8000
pnpm install && pnpm dev                # http://localhost:3000
```

Demo login: **demo@hintro.ai / demo-password-123**

---

## Local development (manual)

**Backend** (Python 3.12, [uv](https://docs.astral.sh/uv/)):

```bash
cd backend
uv sync --extra dev
# Start Postgres + Redis however you like; docker compose up -d db redis is easiest.
uv run alembic upgrade head
uv run python -m scripts.seed
uv run uvicorn app.main:app --reload --port 8000
```

**Frontend** (Node 22, pnpm):

```bash
cd frontend
pnpm install
pnpm dev
```

---

## Environment variables

Backend (`backend/.env`, see `backend/.env.example`):

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | yes | Postgres URL. `postgres://` / `postgresql://` are auto-normalized to the asyncpg driver. Needs the `vector` extension. |
| `JWT_SECRET` | yes | Secret for signing JWTs. |
| `GEMINI_API_KEY` | for AI | Primary LLM and embeddings. Free tier available. |
| `GROQ_API_KEY` | optional | Fallback LLM. |
| `REDIS_URL` | optional | Cache + rate limit. Omitting it degrades gracefully. |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | for Telegram | Reminder delivery + two-way buttons. |
| `DISCORD_WEBHOOK_URL` | for Discord | Reminder delivery. |
| `CRON_SECRET` | yes | Shared secret protecting the reminder job endpoint. |
| `CORS_ORIGIN` | yes | `*` for evaluation. |
| `CANDIDATE_NAME`, `CANDIDATE_EMAIL`, `REPOSITORY_URL`, `DEPLOYED_URL` | yes | Surfaced by `/api/evaluation`. |

Frontend (`frontend/.env.local`): `NEXT_PUBLIC_API_URL` pointing at the API base URL.

---

## API usage examples

```bash
BASE=http://localhost:8000

# Register (or login) and capture the token
TOKEN=$(curl -s -X POST $BASE/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","name":"You","password":"password123"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['token'])")

# Create a meeting with a transcript
MID=$(curl -s -X POST $BASE/api/meetings -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{
    "title":"Sprint Planning",
    "participants":["alice@example.com","bob@example.com"],
    "meetingDate":"2026-05-20T10:00:00Z",
    "transcript":[
      {"timestamp":"00:10","speaker":"John","text":"We should launch next Friday."},
      {"timestamp":"00:20","speaker":"Alice","text":"I will prepare release notes."}
    ]}' | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['id'])")

# Analyze it (grounded insights with citations)
curl -s -X POST $BASE/api/meetings/$MID/analyze -H "Authorization: Bearer $TOKEN"

# Action items, overdue, status update
curl -s "$BASE/api/action-items?status=PENDING" -H "Authorization: Bearer $TOKEN"
curl -s "$BASE/api/action-items/overdue" -H "Authorization: Bearer $TOKEN"
curl -s -X PATCH $BASE/api/action-items/<id>/status -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"status":"COMPLETED"}'

# Standout endpoints
curl -s "$BASE/api/search?q=what+did+we+decide" -H "Authorization: Bearer $TOKEN"
curl -s "$BASE/api/analytics" -H "Authorization: Bearer $TOKEN"

# Trigger the reminder job (normally GitHub Actions cron does this)
curl -s -X POST $BASE/api/jobs/reminders -H "x-cron-secret: <CRON_SECRET>"
```

Every business response is wrapped: `{ "traceId": "...", "success": true, "data": {...} }`. Errors return `{ "traceId": "...", "success": false, "error": { "code", "message", "details?" } }`.

---

## Deployment

**Backend on Render** (Docker blueprint in `render.yaml`):

1. Push the repo to GitHub.
2. Render -> New -> Blueprint -> select the repo. It provisions a free Postgres and the Dockerized API.
3. In the service environment, add `GEMINI_API_KEY` (and optionally `GROQ_API_KEY`, `REDIS_URL` from Upstash, Telegram/Discord secrets).
4. Ensure the `vector` extension is available (the first migration runs `CREATE EXTENSION IF NOT EXISTS vector`). If your Postgres lacks pgvector, use [Neon](https://neon.tech) and set `DATABASE_URL` to its connection string.
5. The container runs migrations on boot, then serves on `$PORT`. Swagger is public at `/api/docs`.

**Frontend on Vercel:**

1. Vercel -> New Project -> import the repo, set the project root to `frontend/`.
2. Set `NEXT_PUBLIC_API_URL` to the Render API URL.
3. Deploy. Update the backend `CORS_ORIGIN` if you want to restrict it (the assignment uses `*`).

---

## Scheduled reminders

The reminder job lives at `POST /api/jobs/reminders` and is protected by the `x-cron-secret` header. `.github/workflows/reminders.yml` calls it every 15 minutes. Set two repository secrets: `API_URL` (the Render URL) and `CRON_SECRET` (matching the API). You can also trigger it manually from the Actions tab. The job finds overdue items, sends Telegram and Discord reminders, records a `ReminderLog`, and dedupes so an item is not reminded more than once per 24 hours.

---

## Testing

```bash
cd backend
uv run pytest -q          # 21 unit + integration tests
uv run ruff check app     # lint
```

The grounding engine has dedicated unit tests proving fabricated citations are dropped and zero-citation insights are discarded. See [TESTING.md](./TESTING.md).

---

## Project structure

See [Architecture](#architecture). The backend is intentionally layered (routes -> services -> models) so logic is testable without HTTP, and the grounding verifier is a pure, deterministic module.

---

## Further docs

- [DECISIONS.md](./DECISIONS.md) - technical decisions, alternatives, trade-offs
- [AI_APPROACH.md](./AI_APPROACH.md) - prompt design, citation strategy, hallucination prevention, limitations
- [TESTING.md](./TESTING.md) - scenarios, edge cases, limitations
- [CHANGELOG.md](./CHANGELOG.md) - milestones
- [CHECKLIST.md](./CHECKLIST.md) - submission checklist

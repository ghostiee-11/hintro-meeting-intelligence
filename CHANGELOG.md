# Changelog

All notable implementation milestones for the Hintro Meeting Intelligence Service.

## 1.0.0

### Foundation
- Monorepo layout: `backend/` (FastAPI) and `frontend/` (Next.js).
- FastAPI app with config (pydantic-settings), structured logging (structlog), and a pure ASGI middleware for trace IDs, request logging, and the unified response envelope.
- Global exception handlers producing the unified error envelope.
- SQLAlchemy 2.0 async models, Alembic migrations, PostgreSQL + pgvector, docker-compose for local Postgres and Redis.
- `/health` and `/api/evaluation` endpoints.

### Auth and cross-cutting concerns
- JWT authentication (register, login, me) with bcrypt password hashing.
- Pydantic v2 request validation with a camelCase API contract.
- Redis-backed caching and fixed-window rate limiting, degrading gracefully without Redis.

### Meeting management
- Create meeting with transcript, get by id, list with pagination and filtering (search, status, date range), scoped to the authenticated user.

### AI analysis and grounding
- LLM provider abstraction with Gemini primary and automatic Groq fallback.
- Indexed-transcript prompt and structured JSON output with defensive normalization.
- Deterministic grounding engine: citation resolution, zero-citation discard, grounding score from coverage + lexical overlap.
- Analyze endpoint plus an SSE streaming variant emitting live progress.
- Transcript embeddings persisted to pgvector for semantic search.

### Action items and reminders
- Action item create, status update, list with filters, and overdue detection.
- Scheduled reminder job (cron-secret protected) with Telegram (two-way buttons) and Discord delivery, reminder history, and 24-hour dedupe.
- Telegram webhook handler to update status from chat.

### Standout features
- Semantic search across meetings (pgvector cosine similarity, keyword fallback).
- Analytics overview (totals, status distribution, workload by assignee, 14-day activity, average grounding score).

### Frontend
- Next.js App Router app with a shadcn-style `components/ui` structure, Tailwind v4, and an emerald/teal brand identity with a custom Hintro waveform logo.
- Landing page with a Spline 3D hero, spotlight, lamp section, and liquid-glass buttons.
- Branded split-screen authentication with a typewriter tagline, wired to the real API.
- Dashboard (KPIs + charts), meetings list with create dialog, meeting detail with an interactive transcript and click-to-source citations plus live streaming analysis, an action-item Kanban board, and semantic search.

### DevOps, testing, docs
- Dockerfile and `.dockerignore` for the API, docker-compose for the full local stack.
- GitHub Actions CI (lint, migrate, pytest against a pgvector service; frontend build) and a scheduled reminders workflow.
- `render.yaml` blueprint for the backend.
- 21 passing unit and integration tests.
- README, DECISIONS, AI_APPROACH, TESTING, CHANGELOG, and CHECKLIST documentation.

# Technical Decisions

This document records the important technical decisions, the alternatives considered, and the trade-offs. The guiding principle throughout was the assignment's own note: a simple, well-engineered solution is preferred over an overly complex one.

## Backend framework: FastAPI

**Chosen:** FastAPI (Python 3.12) with async SQLAlchemy.
**Alternatives:** Django REST Framework, Flask, Node/NestJS.
**Why:** FastAPI gives first-class async (important for I/O-bound LLM and integration calls), automatic OpenAPI/Swagger, and Pydantic validation with almost no boilerplate. DRF is heavier and sync-first; Flask needs many add-ons to reach the same baseline.
**Trade-offs:** FastAPI leaves more architectural choices to you (project layout, error handling), which we addressed with an explicit layered structure (routes -> services -> models) and centralized middleware.

## Database: PostgreSQL + pgvector

**Chosen:** PostgreSQL 16 with the `pgvector` extension, via SQLAlchemy 2.0 async + asyncpg.
**Alternatives:** MongoDB, SQLite, MySQL, a separate vector DB (Pinecone/Qdrant).
**Why:** The domain is a strongly relational graph (meeting -> segments -> insights/action-items -> citations). Foreign keys and cascades enforce integrity that a document store would push into application code. `pgvector` adds semantic search in the same database, so there is no second datastore to operate. SQLite cannot host pgvector or concurrent writes well.
**Trade-offs:** Requires the `vector` extension to be available. The first migration runs `CREATE EXTENSION IF NOT EXISTS vector`; on managed hosts without it, Neon is a drop-in alternative.

## ORM and migrations: SQLAlchemy 2.0 (async) + Alembic

**Chosen:** SQLAlchemy 2.0 typed ORM with Alembic migrations.
**Alternatives:** SQLModel, Tortoise ORM + Aerich, raw SQL.
**Why:** SQLAlchemy is the most battle-tested Python ORM, has strong async support, and pgvector integrates cleanly via `pgvector.sqlalchemy.Vector`. Alembic is the standard migration tool and autogenerates from the models. SQLModel is elegant but thinner for complex queries; Tortoise has a smaller ecosystem.
**Trade-offs:** SQLAlchemy 2.0 has a learning curve. Async relationship loading requires explicit eager loading (`selectinload`), which we use consistently to avoid lazy-load surprises.

## Citations as a first-class table

**Chosen:** A `citations` table that references a transcript segment and belongs to either an insight or an action item.
**Alternatives:** Storing citations as a JSON column on each insight.
**Why:** Making citations real rows means grounding is queryable and verifiable with foreign keys, and a citation can be tied to the actual `TranscriptSegment` row it was verified against. This is central to the anti-hallucination guarantee.
**Trade-offs:** Slightly more write complexity; worth it for integrity and queryability.

## Authentication: JWT

**Chosen:** Stateless JWT (HS256) with bcrypt password hashing.
**Alternatives:** Server-side sessions, OAuth.
**Why:** JWT needs no server-side session store, scales horizontally, and suits a SPA plus a public API the evaluators call directly. bcrypt is the standard for password storage.
**Trade-offs:** Tokens cannot be revoked before expiry without extra infrastructure; acceptable for this scope. We use the `bcrypt` library directly rather than passlib because recent passlib releases are incompatible with bcrypt 4.x.

## LLM provider: Gemini primary, Groq fallback

**Chosen:** A provider abstraction that tries Google Gemini first and automatically falls back to Groq.
**Alternatives:** A single provider (OpenAI/Claude/Gemini/Groq).
**Why:** A free, generous tier (Gemini) keeps the public demo callable at no cost, and an automatic fallback means a transient outage or quota limit on the primary does not break the demo, which is exactly when evaluators hit it. Both support constrained JSON output.
**Trade-offs:** Two SDKs to maintain and prompt-portability to keep in mind. The grounding layer is provider-agnostic, so output quality differences are absorbed by deterministic verification.

## Grounding: deterministic verification, not prompt-trust

**Chosen:** The model cites integer transcript-segment indices; a pure, LLM-free verifier then confirms each citation resolves to a real segment, drops the ones that do not, discards any insight with zero verified citations, and computes a grounding score from citation coverage plus lexical overlap.
**Alternatives:** Trusting the model to cite correctly; using an LLM to grade its own output.
**Why:** Most submissions "ask the model to cite" and hope. Integer indices are far harder to fabricate than free-form timestamps and are trivially checkable. Enforcing the citation rule in code makes "every insight has at least one citation" true by construction. See [AI_APPROACH.md](./AI_APPROACH.md).
**Trade-offs:** Lexical overlap is a heuristic; it can under-score a correct paraphrase. We mitigate by keeping verified-but-low-score insights with a visible score rather than dropping them, and by logging drops.

## External integrations: Telegram + Discord

**Chosen:** Two integrations. Telegram is two-way (inline buttons update status from chat); Discord posts rich embeds.
**Alternatives:** A single integration (the minimum), email.
**Why:** Telegram needs no domain or inbound webhook config to send, is free, and supports interactive buttons for a genuinely two-way workflow. Discord webhooks are trivial and visually clear. Doing two exceeds the requirement and de-risks the demo if one is misconfigured.
**Trade-offs:** Two sets of credentials. Both degrade gracefully: if a channel is unconfigured, it is skipped and recorded, never crashing the job.

## Scheduler: GitHub Actions cron

**Chosen:** A GitHub Actions cron calling a secret-protected `POST /api/jobs/reminders`.
**Alternatives:** In-process APScheduler/`node-cron`, a platform cron (Render Cron Job).
**Why:** It is free, requires no always-on worker, and keeps the web service stateless. The endpoint is reusable (manual trigger, platform cron) and protected by a shared secret.
**Trade-offs:** GitHub cron is best-effort and can be delayed under load. Documented as a known limitation; the dedupe window prevents duplicate reminders if it double-fires, and the endpoint can be triggered manually for demos.

## Unified envelope via ASGI middleware

**Chosen:** A pure ASGI middleware sets the trace id, logs the request, and wraps successful JSON in `{ traceId, success, data }`; global exception handlers produce the matching error envelope. `/health` and `/api/evaluation` are excluded to match their fixed raw contracts.
**Alternatives:** Wrapping in each endpoint, or a `BaseHTTPMiddleware`.
**Why:** Centralizing the envelope keeps controllers clean and guarantees consistency. A pure ASGI middleware (rather than Starlette's `BaseHTTPMiddleware`) was chosen specifically so it does not buffer the SSE streaming endpoint, which `BaseHTTPMiddleware` would break.
**Trade-offs:** Pure ASGI is lower-level; the implementation is small and well-commented.

## Frontend: Next.js (App Router) + Tailwind

**Chosen:** Next.js 16, React 19, TypeScript, Tailwind v4, with a shadcn-style `components/ui` structure and selected premium components (Spline 3D, spotlight, lamp, liquid-glass buttons).
**Alternatives:** A plain Vite SPA, server-rendered templates.
**Why:** Next.js deploys to Vercel with zero config, supports the SSE analysis stream, and the component structure keeps UI primitives reusable. The premium components give the product a distinctive, non-generic identity.
**Trade-offs:** A heavier toolchain than a static SPA; justified by the deployment story and UX quality.

## Caching and rate limiting: Redis, optional

**Chosen:** Redis (Upstash in production) for short-TTL analytics caching and fixed-window rate limiting, behind a wrapper that degrades to no-ops if Redis is absent.
**Alternatives:** In-memory caching, no rate limiting.
**Why:** Rate limiting protects the auth and analyze endpoints (the latter costs LLM quota). Caching keeps the dashboard snappy. Graceful degradation means local dev and CI need no Redis.
**Trade-offs:** Fixed-window limiting is simpler than a token bucket and can allow short bursts at window edges; acceptable here.

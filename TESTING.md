# Testing

> Hintro Meeting Intelligence. [Live app](https://hintro-meeting-intelligence.vercel.app) · [API](https://hintro-meeting-intelligence-i2zr.onrender.com) · [Swagger](https://hintro-meeting-intelligence-i2zr.onrender.com/api/docs) · [Repo](https://github.com/ghostiee-11/hintro-meeting-intelligence). Full overview and requirements coverage in [README](./README.md).

## How to run

```bash
cd backend
uv run pytest -q          # unit + integration (21 tests)
uv run ruff check app     # lint
```

CI (`.github/workflows/ci.yml`) runs the same suite against a `pgvector/pgvector:pg16` service on every push and PR, and builds the frontend.

## Test strategy

Tests target logic that can actually break, not coverage vanity. The grounding engine (the anti-hallucination backbone) and input validation get the most attention.

### Unit tests (no database)

`tests/test_grounding.py` proves the grounding guarantee:

- A valid citation is kept and resolved to the real transcript segment row.
- A fabricated citation (segment index that does not exist) is dropped.
- An insight with zero citations is discarded entirely (the "every insight is cited" rule, enforced by construction).
- A partly-invalid citation set keeps only the valid citations and lowers the grounding score.
- Text that overlaps its cited segment scores higher than text that does not.
- Action items keep assignee and parse due dates; an invalid due date becomes `null` instead of raising.
- Insight types (summary, decision, follow-up) are assigned correctly.

`tests/test_json_util.py` covers defensive parsing of LLM output: fenced JSON, raw JSON, missing-object errors, bare-number citations, snake_case keys, empty-text filtering, and empty input.

### Integration tests (against Postgres)

`tests/test_api.py` exercises the HTTP surface via an in-process ASGI client:

- `/health` returns the raw `{ status: "UP", checks }` contract (not enveloped).
- `/api/evaluation` returns the raw candidate block.
- Validation errors return the enveloped `VALIDATION_ERROR` with field details and a `traceId`.
- Unauthorized access returns the enveloped `UNAUTHORIZED`.
- Every response carries an `x-trace-id` header.
- Full workflow: register -> create meeting -> list (pagination) -> create overdue action item -> appears in `/overdue` -> update status to COMPLETED -> no longer overdue.
- An invalid status value on the PATCH endpoint is rejected with `VALIDATION_ERROR`.

## Edge cases considered

- **Grounding:** zero citations, out-of-range indices, duplicate citations (de-duplicated), partly-valid citation sets, unparseable due dates.
- **Overdue boundary:** items with no due date are never overdue; completed-but-past items are excluded; the comparison is `status != COMPLETED AND dueDate < now`.
- **LLM output:** fenced/chatty responses, snake_case vs camelCase keys, citations as bare integers or objects, malformed entries dropped.
- **Provider failure:** if Gemini fails, Groq is tried; if all fail, the analyze endpoint returns `UPSTREAM_ERROR` and the meeting is marked `FAILED` rather than hanging.
- **Reminder dedupe:** the same item is not reminded more than once per 24 hours per channel even if the cron double-fires; failures are recorded as `FAILED`, not dropped.
- **Redis absence:** caching and rate limiting degrade to no-ops; the app still works (tests run with Redis disabled).
- **Cross-event-loop DB access:** tests use `NullPool` so async connections are never shared across pytest's per-test event loops.

## Manual verification performed

- Started Postgres (pgvector) + Redis via docker-compose, ran migrations and the seed.
- Confirmed `/health`, `/api/evaluation`, register/login, meeting create, validation errors, unauthorized, and the trace header against the live server with curl.
- Loaded the frontend against the live API and verified the landing, auth, and dashboard (KPIs, charts, grounding score, workload) render with real seeded data.

## Limitations discovered

- **LLM-dependent paths need a key.** The analyze and semantic-search-with-embeddings paths require `GEMINI_API_KEY` (or `GROQ_API_KEY`). Without a key, analyze returns a clean `UPSTREAM_ERROR` and search falls back to keyword matching. The grounding logic itself is fully unit-tested without any key.
- **GitHub Actions cron timing** is best-effort and can be delayed; see [DECISIONS.md](./DECISIONS.md). The dedupe window makes this safe.
- **Lexical grounding score** is a heuristic and can under-rate a correct paraphrase; such insights are kept with a visible low score rather than dropped.

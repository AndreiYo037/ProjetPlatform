# Projet

Proof-of-work hiring infrastructure. Runs challenge-based programmes end to end
and turns every participant's output into a durable, verifiable profile.

This repository currently contains the **foundation slice**: the schema, the
outbox, the scheduler, the Google Workspace client, and the seeded 75-role
taxonomy. Product screens land from Milestone 1 onward.

## Layout

```
apps/api/      FastAPI service, SQLAlchemy models, Alembic migrations
apps/web/      Next.js scaffold; API types generated from the OpenAPI schema
content/       the canonical role taxonomy, as markdown — see below
docs/          decisions.md: where this departs from the PRD, and why
```

## Running it

```bash
cd apps/api
uv venv --python 3.11 && . .venv/bin/activate
uv pip install -e ".[dev]"

alembic upgrade head          # defaults to sqlite:///./projet.db
projet-seed                   # loads the 75 roles from ../../content
uvicorn projet.main:app --reload
```

```bash
cd apps/web
pnpm install
pnpm gen:api                  # regenerate types from apps/api/openapi.json
pnpm dev
```

Point `PROJET_DATABASE_URL` at Postgres for anything real. Every setting is
`PROJET_`-prefixed; see `apps/api/projet/config.py`.

## The content directory is the source of truth

`content/` holds the role taxonomy as markdown, and the seed loader parses it
directly — editing a role is content work, not a deploy (FR-044).

| File | Holds |
|---|---|
| `rubrics.md` | universal slots 1 and 4, then slot 2/3 criteria per role |
| `resources.md` | public sources, company asks by `[E]`/`[M]`/`[H]` tier, student tools |
| `deliverables.md` | the default deliverable per role, plus the universal memo |
| `skills.md` | ranked hard/soft skills and search aliases per role |
| `slugs.lock` | committed name → slug snapshot |

The first three documents are cross-cutting: each covers all 75 roles for one
aspect. The loader joins them on role name and **fails unless every role appears
in every file**, so a rename in one place cannot silently strip a role of its
deliverable.

```bash
projet-seed --check        # parse and validate, write nothing (runs in CI)
projet-seed                # load, idempotently
projet-seed --write-lock   # record a deliberate rename in slugs.lock
projet-verify-sources      # fetch and stamp data-pack sources; report readiness
```

**`content/skills.md` is derived and needs review** — it was generated from each
role's rubric criteria and deliverable, and it drives what judges see when
tagging skills.

**No data-pack source is verified yet.** The resource map names sources without
URLs; all 340 entries are seeded `unverified`. Filling those in is the remaining
Milestone 0 work, and `projet-verify-sources` reports what is outstanding.

## Google Workspace

One service account with domain-wide delegation impersonating
`programs@projet.sg`. Without credentials the app selects an in-memory fake, so a
fresh clone and the whole test suite run with no setup.

```bash
export PROJET_GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/sa.json
export PROJET_GOOGLE_DRIVER=real
```

The real driver has **not** been exercised against live Google APIs — see
`docs/decisions.md`.

## Tests

```bash
cd apps/api && . .venv/bin/activate
python -m pytest -q
ruff check projet tests && mypy
```

Tests run on SQLite locally because no Postgres server is available in the build
environment; CI runs the same suite against `postgres:16`, which is where JSONB,
native UUID, timestamptz and the expression index are actually proved.

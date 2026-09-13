# Projet — Development notes

## Architecture

- **Backend**: FastAPI + SQLAlchemy 2.0 in `apps/api/`
- **Frontend**: Next.js 16 App Router + TypeScript in `apps/web/`
- **Design system**: Plain CSS (`globals.css`), no Tailwind — use existing classes (`card`, `panel`, `notice`, `field`, `btn`, `tag`, `row`, `facts`)
- **API client**: `apps/web/lib/api.ts` — typed wrappers around `fetch`, auto-routed through `/backend` proxy in browser
- **Actor gating**: `useActor("company_user" | "participant" | "platform")` on the frontend; `require_actor`, `require_company_manager`, `require_platform` on the backend

## Route guard invariant

`apps/api/tests/test_route_guards.py` walks every registered route and fails if any endpoint lacks `require_actor` in its dependency tree and is not in the `PUBLIC` allowlist. When adding a new public endpoint, add it to `PUBLIC` with a one-line reason. When adding a protected endpoint, ensure the route's dependency eventually calls `require_actor`.

## Lessons

1. **Verify end-to-end flows, not just individual features.** When multiple contributors build different parts (e.g. signup flow via Cursor, challenge listing via Claude), check that the full user journey works: sign up → create challenge → publish → visible in listings. Building display pages without a creation path means nothing is visible.

2. **Company self-serve is the default.** Companies must be able to create and publish their own challenges. Do not gate programme creation/publishing to `require_platform` unless there is a specific reason.

3. **Regenerate `openapi.json` after any API change.** The committed schema drives `pnpm gen:api` which generates `apps/web/lib/api-types.ts`. A stale schema means the frontend types drift from the actual API.

4. **Do not commit pnpm lockfile format changes.** Running `pnpm install` on a different pnpm version can rewrite the lockfile format (e.g. v6 → v9). If the only change is format, revert it.

5. **When the user asks "where is X," answer directly.** State what exists and what doesn't. Do not explain architecture before answering the question.

## Secrets

- `.env` files are gitignored — never commit them
- The admin code in `.env` must never be pushed

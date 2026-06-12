# CLAUDE.md

## Stack And Versions

This project is a greenfield SaaS app using:

- Next.js 15 with the App Router in `app/`.
- React Server Components by default, Client Components only at interaction boundaries.
- TypeScript with `strict` enabled.
- SQLite as the system of record, using `better-sqlite3` for local/server deployments or Turso/libSQL when remote SQLite is required.
- SQL migrations checked into the repository.
- Server Actions or Route Handlers for mutations; never direct database writes from Client Components.

Reason: this stack is fastest when the server owns data access, SQLite stays simple and explicit, and the client receives only the state it needs.

## Project Structure

Use this layout unless there is a strong reason to diverge:

```text
app/
  (marketing)/
  (app)/
  api/
  layout.tsx
  page.tsx
components/
  ui/
  forms/
  app-shell/
db/
  client.ts
  migrations/
  schema.sql
features/
  billing/
  organizations/
  projects/
  users/
lib/
  auth/
  config.ts
  errors.ts
  validation/
tests/
  unit/
  integration/
```

Rules:

- Keep route files thin. Put business logic in `features/<domain>/server/` so it can be tested without rendering a page.
- Keep shared visual primitives in `components/ui/`; keep domain-aware components inside `features/<domain>/components/`.
- Put all database access behind functions in `features/<domain>/server/queries.ts` or `mutations.ts`.
- Keep `db/client.ts` as the only place that opens a SQLite connection.

Reason: thin routes make App Router behavior predictable, and feature folders keep SaaS domains from turning into a shared `lib/` junk drawer.

## Naming Conventions

- Files and folders: kebab-case, such as `project-list.tsx`.
- React components: PascalCase, such as `ProjectList`.
- Server-only functions: verb-first names, such as `createProject`, `listProjects`, `requireCurrentUser`.
- Database tables: snake_case plural nouns, such as `users`, `organizations`, `project_members`.
- Primary keys: `id TEXT PRIMARY KEY`, using generated IDs from app code.
- Timestamps: `created_at`, `updated_at`, stored as ISO-8601 UTC text unless the app already standardizes on Unix milliseconds.

Reason: these conventions map cleanly across React, TypeScript, and SQL without inventing translation rules.

## Dev Commands

Prefer these scripts in `package.json`:

```bash
npm run dev          # start Next.js locally
npm run build        # production build
npm run lint         # lint TypeScript and React
npm run typecheck    # tsc --noEmit
npm run test         # unit/integration tests
npm run db:migrate   # apply pending SQLite migrations
npm run db:reset     # recreate local dev database from migrations
```

When changing code, run the narrowest useful command first, then the full command before the PR is ready.

Reason: fast local feedback keeps changes small, while full checks catch App Router and type integration issues before review.

## SQLite And Migration Rules

- Every schema change gets a numbered migration in `db/migrations/`, for example `0004_add_project_members.sql`.
- Migrations must be deterministic and safe to run once. Do not hide schema changes inside application startup.
- Prefer additive migrations: create new tables/columns, backfill, then switch reads/writes. Avoid destructive changes unless a follow-up cleanup is explicitly planned.
- Always enable foreign keys after opening a connection: `PRAGMA foreign_keys = ON`.
- Use transactions for multi-step writes.
- Keep SQL explicit. Do not introduce an ORM unless the project already uses one.
- For Turso/libSQL, isolate the client implementation behind the same query functions used by local SQLite.

Reason: SQLite is reliable when schema history is visible, connection behavior is deliberate, and writes are scoped by transactions.

## Data Access Pattern

Server code should look like this:

```ts
// features/projects/server/queries.ts
import { db } from "@/db/client";

export function listProjectsForUser(userId: string) {
  return db
    .prepare(
      `select p.id, p.name, p.created_at
       from projects p
       join project_members pm on pm.project_id = p.id
       where pm.user_id = ?
       order by p.created_at desc`,
    )
    .all(userId);
}
```

Rules:

- Validate input at the boundary with a schema in `lib/validation/` or the feature folder.
- Authorize before reading or mutating user-owned data.
- Return plain serializable objects from server functions.
- Do not pass raw database rows directly into Client Components if they contain private fields.

Reason: SaaS bugs usually come from missing authorization and accidental data leakage, not from SQL syntax.

## Component Patterns

- Start with Server Components. Add `"use client"` only for local state, browser APIs, forms with optimistic UI, or interactive widgets.
- Pass data into Client Components as minimal props.
- Keep form components small: UI in the Client Component, validation and mutation in a Server Action or Route Handler.
- Use accessible form labels, button states, and error messages from the first pass.
- Prefer composition over global state. If state is URL-addressable, put it in the URL.

Reason: App Router performance depends on keeping the client bundle small and moving data work to the server.

## Route And API Patterns

- Pages fetch data through feature-level server queries.
- Mutations use Server Actions when the caller is a page/form in the app; use Route Handlers for webhooks, external clients, or public API endpoints.
- Return typed error shapes from Route Handlers:

```ts
return Response.json({ error: { code: "UNAUTHORIZED", message: "Sign in required" } }, { status: 401 });
```

- Never expose stack traces, SQL strings, secrets, or raw validation internals to the client.

Reason: predictable API shapes make UI states and tests straightforward, and sanitized errors protect production details.

## Authentication And Tenancy

- Centralize auth helpers in `lib/auth/`.
- Use `requireCurrentUser()` for protected server code.
- Include `organization_id` or equivalent tenant scope on tenant-owned tables.
- Every tenant-owned query must filter by the current tenant or derive access through a membership join.
- Do not trust IDs from route params until ownership is checked.

Reason: multi-tenant SaaS data leaks are severe; authorization must be visible in every query path.

## Environment Variables

- Read environment variables only from `lib/config.ts`.
- Validate required variables at startup or first import with clear error messages.
- Use separate variables for local and production database URLs:

```text
DATABASE_URL=file:./dev.db
TURSO_DATABASE_URL=
TURSO_AUTH_TOKEN=
```

Reason: central config avoids scattered `process.env` reads and makes deployments easier to audit.

## Testing Expectations

- Unit test pure feature logic and validation.
- Integration test database queries against a temporary SQLite database built from migrations.
- Test authorization failures, not just happy paths.
- For Server Actions and Route Handlers, test input validation and returned error shapes.
- Add regression tests for every bug fix that touches data access, auth, billing, or migrations.

Reason: SQLite makes realistic integration tests cheap, so there is little value in mocking the most important layer.

## Anti-Patterns To Avoid

- Do not put database queries in Client Components. They cannot run there and usually imply leaked secrets.
- Do not add `"use client"` to entire route trees. It bloats bundles and disables Server Component benefits.
- Do not mutate SQLite schema automatically during request handling. It makes production behavior unpredictable.
- Do not store money as floating point numbers. Store integer cents or the payment provider amount unit.
- Do not create catch-all utility files like `lib/helpers.ts`. Name modules after the domain or behavior.
- Do not skip authorization because a page is already "protected". Server functions can be reused from other routes.
- Do not add background jobs without an idempotency key and retry story.

Reason: these shortcuts are cheap in a demo and expensive in a SaaS product with real users and data.

## PR Checklist

Before handing work back:

- New routes are thin and delegate to feature-level server code.
- Database changes include migrations and tests.
- Queries enforce user or tenant ownership.
- Client Components are used only where interactivity requires them.
- `npm run typecheck`, `npm run lint`, and the relevant tests pass or the limitation is documented.
- README or feature docs are updated when setup, env vars, or commands change.

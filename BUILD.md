# Studio Sunny HQ — How it was built

Internal company OS for Studio Sunny (Hyderabad). One login, one workspace: clients, projects, people, finance, and Sunny AI.

This document covers **stack, architecture, design system (colors, fonts, motion), product surface, and how to run it.**

---

## 1. Product intent

Feel: **Mercury + Attio + Stripe Dashboard + Linear** — not a generic HR/PM clone.

- Dark by default (onyx / champagne / periwinkle)
- Editorial display type + dense sans UI
- Real data, real RBAC, real workflow — Phase 1 is a working vertical slice, not a mock

Long-term domains:

| Host | Role |
| --- | --- |
| `hq.studiosunny.com` | Employee HQ (this app) |
| `client.studiosunny.com` | Future client portal, same API, stricter RBAC |
| `studiosunny.com` | Public site |
| `careers.studiosunny.com` | Future recruiting |

---

## 2. Tech stack

### Frontend (`frontend/`)

| Piece | Choice | Why |
| --- | --- | --- |
| Framework | **Next.js 16** (App Router) | Routes, fonts, production shell |
| Language | **TypeScript** | Typed API + UI |
| UI runtime | **React 19** | Current Next default |
| Styling | **Tailwind CSS v4** + CSS variables | Token-driven light/dark |
| Data fetching | **TanStack Query v5** | Cache, invalidation after mutations |
| Client state | **Zustand** | Sidebar, ⌘K, quick create |
| Theme | **next-themes** | Dark / light / system (`class` on `<html>`) |
| Icons | **Lucide** | Stroke 1.75, 16px in nav |
| Command palette | **cmdk** | ⌘K / Ctrl+K search + actions |
| Toasts | **Sonner** | Bottom-right, token-colored |
| Dates | **date-fns** | Relative + formatted dates |
| Motion | **Framer Motion** (installed) + CSS | Page enter, hover lift |
| Class merge | **clsx** + **tailwind-merge** | `cn()` helper |
| Fonts | **next/font/google** | Plus Jakarta Sans, Fraunces, Geist Mono |

**Not used:** shadcn/ui, Material, Bootstrap, AI-generated component kits.

### Backend (`backend/`)

| Piece | Choice |
| --- | --- |
| API | **FastAPI 0.116** + Uvicorn |
| ORM | **SQLAlchemy 2** |
| Schemas | **Pydantic v2** + pydantic-settings |
| Auth | **JWT** (HS256) in **httpOnly cookies** `ss_access` / `ss_refresh` |
| Passwords | **passlib** + **bcrypt 4.0.1** |
| Migrations | **Alembic** (ready; local demo uses `create_all`) |
| HTTP client / tests | **httpx**, **pytest** |
| JSON | **orjson** |

### Data & infra

| Piece | Choice |
| --- | --- |
| Production DB | **PostgreSQL 16** (`docker-compose.yml`) |
| Local fallback | **SQLite** `backend/studio_sunny_hq.db` |
| Cache (optional) | **Redis 7** (compose; not required for Phase 1) |
| CORS | `http://localhost:3000` → API `:8000` |

### Local URLs

- HQ UI: `http://localhost:3000`
- API: `http://localhost:8000`
- Health: `http://localhost:8000/health`
- API prefix: `/api/v1`

---

## 3. How to run

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python -m app.seed.seed
# Empty platform (founder only). Mock dataset: python -m app.seed.seed --reset --demo
uvicorn app.main:app --reload --port 8000

# Frontend (second terminal)
cd frontend
npm install
npm run dev
```

Optional Postgres:

```bash
docker compose up -d
# then set DATABASE_URL in backend/.env and re-seed
```

### First login

After bootstrap: `sunny@studiosunny.com` / `SunnyHQ2026!`. Add real team and clients in HQ. Full mock cast (Arjun/Rahul/… + Muttonly) is only via `--demo`.

---

## 4. Repository layout

```
Studio Sunny/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/   # auth, dashboard, desk, clients, projects…
│   │   ├── core/               # config, JWT, RBAC
│   │   ├── db/                 # session, portable UUID/JSON types
│   │   ├── models/             # SQLAlchemy entities
│   │   ├── schemas/            # Pydantic DTOs
│   │   ├── services/           # activity, project, Sunny AI
│   │   └── seed/seed.py
│   └── tests/test_workflow.py
├── frontend/
│   ├── app/
│   │   ├── login/page.tsx
│   │   ├── (hq)/               # authenticated shell routes
│   │   ├── globals.css         # design tokens
│   │   └── layout.tsx          # fonts + providers
│   ├── components/
│   │   ├── ui.tsx              # Button, Badge, PageHeader…
│   │   ├── shell/              # sidebar, topbar, ⌘K, quick create
│   │   ├── mark.tsx            # gold→periwinkle “S”
│   │   ├── sparkline.tsx
│   │   ├── health-ring.tsx
│   │   ├── monogram.tsx
│   │   └── live-clock.tsx      # IST
│   ├── lib/                    # api.ts, auth.tsx, utils.ts
│   └── stores/ui.ts
├── docker-compose.yml
├── .env.example
├── README.md
└── BUILD.md                    # this file
```

---

## 5. Architecture

```
Browser (Next.js :3000)
   │  fetch + credentials: "include"
   ▼
FastAPI (:8000)  /api/v1/*
   │  JWT cookies  ss_access / ss_refresh
   │  RBAC via role → permission matrix
   ▼
PostgreSQL or SQLite
```

- Frontend never stores the JWT in `localStorage`. Cookies are httpOnly.
- On `401`, the client redirects to `/login`.
- Mutations invalidate related TanStack Query keys (`dashboard`, `desk`, `tasks`, `notifications`…).
- Sensitive fields (salary, invoices, credentials) are **server-enforced**. Sunny AI uses the same permission checks — no LLM, rules + DB only.

### Auth cookies

| Cookie | Lifetime |
| --- | --- |
| `ss_access` | 30 minutes |
| `ss_refresh` | 14 days |

SameSite=`lax`. `COOKIE_SECURE=false` in local dev.

### Roles

`founder`, `operations_manager`, `project_manager`, `developer`, `designer`, `automation_engineer`, `marketing`, `sales`, `finance`, `freelancer`

Permissions look like `clients:read`, `finance:write`, `employees.compensation:read`, `ai:use`. Founder has `*`.

---

## 6. Design system (Phase 0 retune)

**In-app:** hairline elevation, 14px Plus Jakarta Sans, no film grain / aurora / button glow. Fraunces only on auth, empty states, and marketing. Champagne + periwinkle stay as a two-accent system used sparingly.

See also Phase 0–1 in the upgrade plan: Argon2id, refresh rotation + reuse detection, CSRF (`ss_csrf` + `X-CSRF-Token`), jti denylist, and Redis-backed chat/presence.

Phase 1 also ships Postgres RLS + `org_id` (SQLite no-ops RLS), append-only `/audit`, typed OpenAPI (`frontend/openapi.json` + `lib/api-schema.d.ts` + TanStack `queryOptions`), `useOptimistic` on chat/task, and TanStack Virtual on chat + board columns. Regenerate types with `python -m scripts.export_openapi` then `npm run gen:api`.

**Docs (Phase 2 start):** TipTap editor at `/docs`, project Docs tab, REST `/api/v1/docs`, seeded handbook + Muttonly brief.

**Files:** local upload cabinet at `/files` + project Files tab, REST `/api/v1/files` (25MB, typed allow-list, credential kind gated, download audited).

**Calendar + board:** `/calendar` month grid from task due dates + milestones; Tasks board uses `@dnd-kit` drag-and-drop with optimistic status.

**Admin audit:** `/admin/audit` live table over `/api/v1/audit` with search/filters and actor names.

**Alembic:** `backend/alembic` + `alembic upgrade head` on API boot (falls back to `create_all`). Postgres is the default `DATABASE_URL`; pytest forces SQLite via `tests/conftest.py`.

## Phase 2 (complete)

| Item | Status |
| --- | --- |
| TipTap + **Yjs** live collab (`/docs/{id}/collab` WS, Redis fan-out, `yjs_state`) | Done |
| Google **SSO/OIDC** + **TOTP 2FA** (Settings + login) | Done (SSO when env set) |
| **Arq** worker digests/standups (`arq app.worker.WorkerSettings`, compose profile `workers`) | Done |
| **CI** GitHub Actions: pytest, lint/build, Playwright, Schemathesis dry-run | Done |
| **Sentry / OTEL / PostHog** env-gated | Done |
| Root `package.json` + `turbo.json` (npm workspaces; pnpm optional later) | Done |

## Post–Phase 2 polish (complete)

| Item | Status |
| --- | --- |
| Reports (`/reports` + `/api/v1/reports`) | Done |
| Admin Integrations / Templates / editable Company settings / Permissions matrix + overrides | Done |
| Credential vault UI (`/vault`) | Done |
| Invite flow + change / forgot / reset password | Done |
| Docs remote carets (Yjs awareness + CollaborationCaret) | Done |
| Arq heartbeat + Integrations live status; SMTP optional for invite email | Done |

## 6b. Legacy notes (pre-Phase 0)

### Inspiration

Mercury (indigo-black surfaces), Attio (warm accent + density), Stripe Dashboard (money + health), Linear (keyboard + sparse chrome). **Not** Geist-zinc clone, **not** purple-gradient SaaS.

Default theme: **dark**. Light theme exists as a warm ivory alternative.

---

### 6.1 Fonts (Google via `next/font`)

| Role | Family | Weights | Used for |
| --- | --- | --- | --- |
| UI sans | **Plus Jakarta Sans** | 400, 500, 600, 700 | Body, nav, tables, buttons |
| Display | **Fraunces** | 400, 500, 600 | Page titles (`PageHeader`, Home greeting) |
| Mono | **Geist Mono** | default | `<kbd>`, code-ish chips |

CSS variables: `--font-sans`, `--font-display`, `--font-mono`.

**Type rules**

| Token | Size | Tracking | Notes |
| --- | --- | --- | --- |
| Body | **13px** | `-0.012em` | `line-height: 1.5`, antialiased |
| Display H1 | **34–46px** | `-0.03em` | Fraunces 500 |
| Kicker | **11px** | `0.14em` uppercase | Section labels |
| Section title | **13px** / 600 | `-0.01em` | |
| Badge / meta | **11–12px** | | |
| KPI / money | **20–28px** tabular | | Champagne on hero numbers (`.gold-num`) |
| Keyboard | **10px** Geist Mono | | |

---

### 6.2 Color tokens

Defined in `frontend/app/globals.css`. Tailwind maps them via `@theme inline` as `bg`, `raised`, `elevated`, `sunken`, `ink`, `muted`, `line`, `accent`, `accent-2`, `accent-fg`, `ok`, `warn`, `danger`.

#### Dark (default) — onyx / champagne / periwinkle

| Token | Hex / value | Role |
| --- | --- | --- |
| `--bg` | `#12121a` | Canvas (indigo-black) |
| `--bg-raised` | `#1a1a24` | Sidebar, inputs, cards |
| `--bg-elevated` | `#22222e` | Hover / popovers |
| `--bg-sunken` | `#16161f` | Tracks, wells, kanban columns |
| `--ink` | `#f1f0ec` | Primary text (ivory) |
| `--ink-soft` | `#a8a6b3` | Muted / kickers |
| `--line` | `rgba(241,240,236,0.09)` | Hairline borders |
| `--accent` | `#e8b86d` | **Champagne gold** — primary CTA, live rail, numbers |
| `--accent-2` | `#8b9bff` | **Periwinkle** — info, aurora, gradient end |
| `--accent-fg` | `#1a150c` | Text on gold buttons |
| `--ok` | `#3dcb9a` | Healthy / paid / available |
| `--warn` | `#e8b86d` | Attention / outstanding |
| `--danger` | `#f07a6a` | Risk / overdue / blocked |
| `--info` | `#8b9bff` | Hyderabad chip, info badges |
| `--glow` | `rgba(232,184,109,0.28)` | Button + panel glow |

#### Light — warm ivory / bronze / indigo

| Token | Hex / value | Role |
| --- | --- | --- |
| `--bg` | `#f4f1ea` | Canvas |
| `--bg-raised` | `#fffcf6` | Surfaces |
| `--bg-elevated` | `#fff8ee` | Elevated |
| `--bg-sunken` | `#ebe6dc` | Wells |
| `--ink` | `#1c1914` | Text |
| `--ink-soft` | `#6d675c` | Muted |
| `--line` | `rgba(28,25,20,0.10)` | Borders |
| `--accent` | `#9a6428` | Bronze gold |
| `--accent-2` | `#4f5fd6` | Indigo |
| `--accent-fg` | `#fff8ef` | On-accent text |
| `--ok` | `#1f8a5a` | |
| `--warn` | `#b45309` | |
| `--danger` | `#c2413b` | |
| `--info` | `#4f5fd6` | |
| `--glow` | `rgba(154,100,40,0.22)` | |

#### Avatar / monogram gradients

1. Champagne `#e8b86d → #9a6428`
2. Periwinkle `#8b9bff → #4f5fd6`
3. Emerald `#3dcb9a → #1f8a5a`
4. Coral `#f07a6a → #c2413b`
5. Bronze `#c9a36a → #6d4c2b` (monograms only)

Picked by hashing the name. Logo mark (`Mark`) is champagne → periwinkle with inner highlight.

#### Semantic badge tones

`neutral` · `ok` · `warn` · `danger` · `accent` · `info`

---

### 6.3 Shape, space, chrome

| Token | Value |
| --- | --- |
| `--radius` (panels) | **12px** |
| `--control` (inputs / buttons) | **8px** |
| Sidebar width | **240px** / **68px** collapsed |
| Topbar height | **56px** (`h-14`) |
| Content max widths | 1100–1400px depending on page |
| Page padding | `px-4 py-6` / `md:px-7 md:py-7` |
| Card padding | 14–20px |
| Hairline | 1px `var(--line)` |
| Focus ring | 2px champagne, 1px offset |
| Selection | champagne at 28% opacity |

**Panel material**

- Top highlight: `linear-gradient` ink 4.5% → raised
- Inset 1px highlight + drop shadow
- `.panel-glow` adds champagne ring + glow (AI briefing, overdue, ⌘K, quick create)
- `.lift` hover: translateY(-2px) + champagne border + glow

**Atmosphere**

- `.aurora` — radial champagne (top-right) + periwinkle (top-left) on canvas
- SVG fractal **film grain** overlay at 7% (`mix-blend-mode: overlay`)
- Login: cinematic mesh orbs (periwinkle / champagne / mint) on `#12121a`

**Progress**

- Track: sunken, 4px, pill
- Fill: `linear-gradient(90deg, accent → accent-2)`

---

### 6.4 Motion

| Effect | Timing |
| --- | --- |
| Page enter (`.hq-enter`) | 320ms fade + 8px rise |
| Card lift | 180ms transform / border / shadow |
| Live presence dot | gold/ok glow |
| IST clock | updates every second (`LiveClock`) |

---

### 6.5 Iconography & chrome details

- Lucide, **16px**, stroke **1.75**
- Active nav: champagne 14% fill + **2px gold left rail**
- Sidebar “Live” pill + IST clock
- Topbar: Hyderabad badge, search with champagne icon, ⌘K, New, notifications, theme toggle
- Primary button: gold fill + glow shadow
- Scrollbars: 8px thin, ink at 16%

---

### 6.6 UI primitives (`frontend/components/ui.tsx`)

`Avatar` · `Button` (primary / ghost / outline / danger / subtle) · `Input` · `Textarea` · `Select` · `Badge` · `EmptyState` · `Skeleton` · `PageHeader` · `ComingSoon` · `healthTone()` · `priorityTone()`

Specialized: `Mark`, `Sparkline`, `HealthRing`, `Monogram`, `LiveClock`.

Shell: `HqShell`, `Sidebar`, `Topbar`, `CommandPalette`, `QuickCreate`.

---

## 7. Product surface (Phase 1)

| Route | What it does |
| --- | --- |
| `/login` | Split cinematic sign-in |
| `/home` | Founder KPIs, sparklines, AI briefing, health rings |
| `/desk` | Personal focus, due today, blocked, assigned projects |
| `/projects` | Grid/list + monograms; `/projects/new` 7-step create |
| `/projects/[id]` | Workspace: overview, tasks, timeline, team, activity |
| `/clients` · `/clients/[id]` | Accounts + onboarding steps |
| `/tasks` | Company kanban (status select) |
| `/team` · `/team/[id]` | Directory, capacity rings, compensation gated |
| `/leads` | Pipeline columns (role-gated) |
| `/finance` | Collected / outstanding / overdue + invoices (role-gated) |
| `/ai` | Sunny AI (permission-aware, DB/rules) |
| `/notifications` | Unread gold rail |
| `/calendar` | Month grid + agenda for task due dates and milestones |
| `/messages` | Real-time channels |
| `/files` | Upload cabinet |
| `/docs` | TipTap + Yjs docs |
| `/admin/*` | Employees, departments, permissions, settings, audit |

### End-to-end workflow (seeded)

Founder creates **client → project → PM + team → milestone → tasks → My Desk**. Employee updates task status → progress, activity, notifications, and dashboard refresh.

---

## 8. API map

All under `/api/v1`:

`/auth` · `/dashboard` · `/desk` · `/clients` · `/projects` · `/tasks` · `/employees` · `/notifications` · `/activity` · `/search` · `/ai` · `/leads` · `/invoices`

Frontend client: `frontend/lib/api.ts` (`credentials: "include"`).

---

## 9. Design do / don’t

**Do**

- Champagne for primary action, numbers, active state
- Periwinkle for info, aurora, gradient pair with gold
- Fraunces only on page titles / greeting
- 13px UI, tight tracking, tabular money
- Hairline borders + inner highlight on panels

**Don’t**

- Purple SaaS gradients, Inter-only, 16px “startup landing” type
- Drop shadows as the only depth (use inset highlight + glow sparingly)
- Expose salary / invoices in the UI without matching API permission

---

## 10. Tests

```bash
cd backend
pytest
```

`tests/test_workflow.py` covers the client → project → task → desk path.

---

## 11. Env (`/.env.example`)

```
DATABASE_URL=postgresql+psycopg://sunny:sunny_hq_dev@localhost:5432/studio_sunny_hq
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=change-me-in-production-use-a-long-random-string
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=14
CORS_ORIGINS=http://localhost:3000
COOKIE_SECURE=false
ENVIRONMENT=development
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Local demo works without Docker: SQLite + default secret.

---

*Studio Sunny HQ · Phase 1 · 2026*

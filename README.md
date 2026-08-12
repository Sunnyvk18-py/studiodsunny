# Studio Sunny HQ

Premium internal operating system for Studio Sunny — projects, clients, people, finance, and Sunny AI in one login.

Phase 1 is a working vertical slice, not a mock: **auth → RBAC → founder dashboard → client → project → team → tasks → My Desk → activity → notifications**.

**Full build + design system (colors, fonts, motion, architecture):** see [`BUILD.md`](./BUILD.md).

## Stack

- **Frontend:** Next.js 16, TypeScript, Tailwind CSS v4, TanStack Query, Zustand, Framer Motion-ready, Lucide
- **Fonts:** Plus Jakarta Sans (UI), Fraunces (display), Geist Mono (kbd)
- **Look:** dark onyx `#12121a` · champagne `#e8b86d` · periwinkle `#8b9bff`
- **Backend:** FastAPI, SQLAlchemy 2, Pydantic v2, JWT cookies
- **Database:** PostgreSQL in production (`docker compose`). SQLite for local demo by default.

## Quick start

```bash
# 0. Infra (recommended)
docker compose up -d

# 1. Backend
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
# Optional explicit migrate: alembic upgrade head
python -m app.seed.seed
uvicorn app.main:app --reload --port 8000

# 2. Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Postgres is the default database (`DATABASE_URL` in `.env.example`). For a SQLite-only demo, set:

```
DATABASE_URL=sqlite:///./studio_sunny_hq.db
```

Open [http://localhost:3000](http://localhost:3000).

### Demo accounts

Password for all: `SunnyHQ2026!`

| Email | Role |
| --- | --- |
| sunny@studiosunny.com | Founder |
| arjun@studiosunny.com | Project Manager |
| rahul@studiosunny.com | Developer |
| priya@studiosunny.com | Designer |
| kiran@studiosunny.com | Automation Engineer |

## PostgreSQL (optional)

```bash
docker compose up -d
```

Then set in `backend/.env`:

```
DATABASE_URL=postgresql+psycopg://sunny:sunny_hq_dev@localhost:5432/studio_sunny_hq
```

Re-run seed after switching databases.

## Architecture

```
hq.studiosunny.com      → this app (employee HQ)
client.studiosunny.com  → future client portal, same API, stricter RBAC
studiosunny.com         → public site
careers.studiosunny.com → future recruiting
```

Sensitive fields (salary, invoices, credentials) are **server-enforced**. Sunny AI respects the same permission matrix.

## Phase 1 surface

- Login + session cookies + refresh
- HQ shell (sidebar, command palette `⌘K` / `Ctrl+K`, quick create, light/dark/system)
- Founder home + AI briefing
- My Desk (focus + status updates)
- Clients, projects (7-step create), tasks (kanban statuses)
- Team directory + profiles
- Leads pipeline, finance invoices (role-gated)
- Notifications + activity
- Sunny AI (data-backed, no salary leaks)

## Tests

```bash
cd backend
pytest
```

# Nexus AI — Autonomous Business Data Analyst for E-commerce (PPD II)

A multi-tenant SaaS platform where e-commerce companies (e.g. Meesho) register,
get verified by the platform owner, and then use an agentic AI analyst that
answers business questions over their data using SQL tools and RAG.

## How the platform works

```
Company registers  ->  Super Admin reviews & approves  ->  Company Admin gets access
                                                              |
                                        uploads data, invites colleagues (viewers)
```

| Role | Who | Can do |
|---|---|---|
| **Super Admin** | Nexus AI (platform owner) | Review applications (logo, MD, GSTIN/PAN/CIN, authorization letter, data-access declaration), approve / reject / suspend companies, see audit trail |
| **Company Admin** | The company's finance authority | Full control of the company workspace: manage team access, (Phase 3) upload & maintain data |
| **Member** | Other designations (Ops head, CMO, ...) | View dashboards & ask the analyst. Cannot invite users or change data |

Company status: `pending` -> `approved` (or `rejected` / `suspended`). Users of a
non-approved company can log in only to see their application status.

### Verification (what the Super Admin sees)
Automated sanity checks: GSTIN / PAN / CIN format, **PAN matches the PAN embedded
in the GSTIN**, applicant uses a corporate (non free-mail) email, email domain
matches the company website. Plus the uploaded logo, signatory-letter PDF, MD
details and the declared data access. Checks flag obvious problems only — the
Super Admin makes the final call.

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | React 19, Vite, Tailwind CSS v4, Recharts, React Router |
| Backend | Python, FastAPI |
| Database | SQLAlchemy: SQLite locally (`data/platform.db`), Postgres in production (`DATABASE_URL`); demo business data in `data/ecommerce.db` |
| Auth | Email + password, JWT (scrypt hashing) — isolated in `backend/security.py` so it can be swapped for Supabase / Firebase Auth |
| AI | Rule-based agent + RAG (offline). Optional Claude / OpenAI for answer-writing via env var |

## Run it

```bash
pip install -r requirements.txt
python data/generate_data.py            # once: synthetic e-commerce demo data

uvicorn backend.main:api --port 8000    # terminal 1  (creates platform.db + super admin on first run)

cd frontend && npm install && npm run dev   # terminal 2  -> http://localhost:5173
```

**Super Admin login (local dev only):** `superadmin@nexusai.in` with the dev default password from
`backend/config.py`. In production (`NEXUS_ENV=production`) the app refuses to start unless
`DATABASE_URL`, `NEXUS_SECRET_KEY` and `NEXUS_ADMIN_PASSWORD` are set.

## Deploy on Render (free)

`render.yaml` is a Render Blueprint that creates three things, already wired together:
`nexus-ai-api` (FastAPI), `nexus-ai-web` (the React site) and `nexus-ai-db` (Postgres).

1. Render Dashboard -> **New** -> **Blueprint** -> connect GitHub -> pick this repo -> **Apply**.
2. When asked, enter `NEXUS_ADMIN_PASSWORD` (the Super Admin password, 10+ characters). The JWT secret is generated automatically and the database URL is filled in by Render.
3. Open `https://nexus-ai-web.onrender.com` and sign in as `superadmin@nexusai.in`.

If Render gives a service a different address (e.g. the name was taken), set
`VITE_API_URL` on `nexus-ai-web` to the API's address and `CORS_ORIGINS` on
`nexus-ai-api` to the site's address, then redeploy both.

Free-tier notes: the API sleeps after 15 idle minutes, so the first request afterwards takes up to a
minute. Data lives in Postgres, so it survives sleeps and redeploys. **Render's free Postgres expires
30 days after creation** — before that, upgrade it or point `DATABASE_URL` at another Postgres
(Neon / Supabase). Logos and letters are stored in the database, not on disk.

### Demo script
1. **Register a company** at `/register` (3 steps: company details -> MD & documents -> data access & admin account). Use a valid-format GSTIN/PAN/CIN, e.g. `29ABCDE1234F1Z5` / `ABCDE1234F` / `U74999KA2015PTC123456`; a logo (PNG/JPG/WebP) and any PDF as the letter.
2. Log in as that admin -> sees **"under review"**; cannot reach the dashboard.
3. Log in as **Super Admin** -> review drawer with the verification checks -> **Approve**.
4. Log in as the company admin again -> full dashboard + **Team** page. Add a member (e.g. Head of Operations).
5. Log in as the member -> analyst only; `/team` and `/admin` are blocked.
6. In the analyst: **"Why did sales drop in July?"** — the multi-step agentic reasoning trace.

## Project layout

```
backend/
  main.py            app, startup seeding, analytics endpoints (auth-gated)
  security.py        password hashing, JWT, role dependencies  <- swap point for Supabase
  models.py          Company, User, AuditLog (SQLAlchemy)
  verification.py    GSTIN/PAN/CIN + domain checks for the review screen
  routers/           auth.py (register/login), admin.py (review), company.py (team)
app/                 agent (intent routing + SQL tools + multi-step chains), RAG, LLM abstraction
frontend/src/
  pages/             Login, Register, Status, Admin, Team, Analyst
  auth/              AuthContext (session + role-based home routing)
data/                generate_data.py, docs/ (RAG knowledge base)
```

## Security notes
- Passwords: scrypt with per-user salt. Sessions: signed JWT, 12h expiry.
- Every endpoint checks role **and** company approval on the server; the UI guards are only UX.
- Uploads: extension + size (5 MB) + magic-byte checks; SVG logos refused (script risk); stored in the database. The authorization letter is downloadable only by the Super Admin; logo URLs carry an HMAC signature so they can't be enumerated.
- Not yet: login rate-limiting, email verification, password reset (would come with Supabase Auth).

## Roadmap
- **Phase 3 (next):** company data upload (CSV) with per-company isolation; the agent's SQL is scoped to the caller's `company_id`. **Today every approved company sees the same synthetic demo dataset.**
- Per-designation views (e.g. Marketing sees marketing insights only).
- Replace keyword RAG with embeddings + pgvector; LLM text-to-SQL; multi-agent orchestration (LangGraph); forecasting.
- Move to Supabase (Postgres + Auth + Storage) for production.

> A Streamlit version of the analyst remains (`streamlit_app.py`) as a fallback demo.

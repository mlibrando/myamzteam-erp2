# Deploy — P&L Dashboard (read API + frontend)

Scope: the **dashboard only** — the FastAPI read API on Railway and the Next.js
frontend on Vercel. The sync/ingest cron is **not** part of this deploy.

Architecture:

```
  Vercel (frontend/)                 Railway project (existing — keeps Postgres)
 ┌────────────────────┐              ┌───────────────────────────────────────┐
 │ Next.js dashboard  │  HTTPS +     │  ┌─────────────┐   ┌────────────────┐  │
 │ NEXT_PUBLIC_API_   │──password──▶ │  │ web: uvicorn│──▶│ Postgres 18    │  │
 │ BASE = Railway URL │   header     │  │ app.main    │   │ (existing data)│  │
 └────────────────────┘              │  └─────────────┘   └────────────────┘  │
                                     └───────────────────────────────────────┘
```

> ⚠️ **Never delete the Postgres service.** It holds all reconciled data
> (Jan–Jul 2026, US/CA/UK/AU). "Overwriting the old deploy" means replacing the
> stale **app** service only — the database stays.

---

## 0. Prerequisite — push this repo to GitHub

Railway and Vercel both deploy from GitHub. Make sure `main` (with this commit,
which adds `backend/Dockerfile` + `backend/railway.toml`) is pushed to
`myamzteam-erp2`. `.env` is gitignored and must NOT be committed — secrets go into
the platform dashboards below.

> Build method: **Docker** (`backend/Dockerfile`, Python 3.12-slim), selected via
> `backend/railway.toml`. This mirrors the old project's proven Dockerfile — same
> `alembic upgrade head && uvicorn app.main:app` start command. The only change is
> the healthcheck path: this repo's app serves `/healthz`, not the old `/api/health`.

---

## 1. Railway — backend web service

Do this in the **existing** project that already contains your Postgres.

1. Open the project → **New → GitHub Repo → `myamzteam-erp2`**. This creates a new
   service alongside the existing Postgres. (We add a new service and delete the
   old app later, rather than editing the old one in place.)
2. Service → **Settings → Source**:
   - **Root Directory:** `backend` (required — makes the Docker build context `backend/`
     so the Dockerfile's `COPY` steps and `dockerfilePath` resolve).
   - Railway reads `backend/railway.toml` → builds from `backend/Dockerfile`; the
     start command + migrations are baked into the Dockerfile `CMD`, healthcheck into the toml.
3. Service → **Variables** — add:

   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` — reference the existing Postgres service (use its real service name if not "Postgres"). Resolves to the private `*.railway.internal` URL. |
   | `DASHBOARD_PASSWORD` | a real password — **not** `admin` |
   | `DASHBOARD_ORIGINS` | leave unset for now; set in step 3 after Vercel is up |

   No Amazon / Ads / Google secrets are needed for the dashboard.
4. Service → **Settings → Networking → Generate Domain**. Copy the
   `https://<name>.up.railway.app` URL → this is your **API base**.
5. Deploy. On boot it runs `alembic upgrade head` (a no-op — already at head) then
   uvicorn. Verify: open `https://<name>.up.railway.app/healthz` → `{"ok":true}`.

---

## 2. Vercel — frontend

1. **Add New → Project → import `myamzteam-erp2`**.
2. **Root Directory:** `frontend` (Framework preset auto-detects Next.js).
3. **Environment Variables** — add:

   | Variable | Value |
   |---|---|
   | `NEXT_PUBLIC_API_BASE` | the Railway API URL from step 1.4 (no trailing slash) |

   > This is baked in at **build time**. If the API URL ever changes, you must
   > redeploy the frontend.
4. Deploy. Copy the resulting `https://<app>.vercel.app` URL.

---

## 3. Close the CORS loop (back on Railway)

The API rejects cross-origin requests it doesn't recognise. Now that the frontend
URL exists:

1. Railway → web service → **Variables** → set:

   | Variable | Value |
   |---|---|
   | `DASHBOARD_ORIGINS` | `https://<app>.vercel.app` (comma-separate extra origins / custom domain if any) |

2. Railway redeploys automatically on the variable change. Done.

Without this, the deployed dashboard loads but every `/pnl` fetch fails with an
opaque CORS error in the browser console.

---

## 4. Retire the old deployment

Once the new dashboard works end-to-end, delete the **old app service** in the
project (the one serving `myamzteam-erp-production.up.railway.app`). Leave the
Postgres service untouched.

---

## Ordering (the chicken-and-egg)

API needs the frontend origin (CORS); frontend needs the API URL. So:

**API deploy → get API URL → Vercel deploy → get Vercel URL → set `DASHBOARD_ORIGINS` → API redeploys.**

## Env var summary

| Where | Variable | Purpose |
|---|---|---|
| Railway (web) | `DATABASE_URL` | existing Postgres (reference variable) |
| Railway (web) | `DASHBOARD_PASSWORD` | server-side password gate |
| Railway (web) | `DASHBOARD_ORIGINS` | CORS allowlist = Vercel URL(s) |
| Vercel | `NEXT_PUBLIC_API_BASE` | Railway API URL (build-time) |

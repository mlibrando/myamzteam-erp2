# P&L Dashboard (v1)

Month-as-column P&L grid that replaces Elena's manual Sellerise sheet. Read-only: FastAPI
endpoint over `pnl_monthly` + `ad_spend_daily`, Next.js grid. Mapping is
`reference/data/pnl_dashboard_probe.md` verbatim (a whitelist — `passthrough` never enters a row).

## Run

**Backend** (from `backend/`, needs `DATABASE_URL` in `../.env`):

```bash
export DASHBOARD_PASSWORD='<shared password>'      # required; auth is checked server-side
# optional: export DASHBOARD_ORIGINS='http://localhost:3000'   # CORS allowlist
.venv/bin/python -m uvicorn app.main:app --port 8000
```

`GET /pnl?marketplace={US|CA|UK|AU|ALL}` with header `X-Dashboard-Password: <password>`.
Returns the assembled grid (rows × settled months + total + a Net row) and the view's currency.

**Frontend** (from `frontend/`):

```bash
yarn install
# optional: export NEXT_PUBLIC_API_BASE='http://localhost:8000'   # default
yarn dev            # or: yarn build && yarn start
```

Open http://localhost:3000, enter the shared password (kept in `sessionStorage` for the session),
pick a marketplace.

## What it shows

- Rows in Elena's order: Sales, COGS, Ad Spend, Selling Fees, Operational Fees, Refunds,
  Reimbursements from AMZ, then Net. All settled months (Jan–Jun 2026) as columns + a Total column.
- **Currency:** single marketplace → native (US=USD, CA=CAD, UK=GBP, AU=AUD); **All → USD** at Elena's
  fixed book rates (GBP×1.34, CAD×0.71, AUD×0.69, in `app/pnl.py`). CA/AU `cog` is stored in USD and is
  converted like any USD value — never double-converted.
- **Ad Spend** comes from `ad_spend_daily` (not in `pnl_monthly`).
- An inline note flags that the Operational Fees / Reimbursements **split** is provisional (their
  combined total is reconciled).

Correct Amazon figures only — no in-UI divergence explanations (those live in the probe doc §8).

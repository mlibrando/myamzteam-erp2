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
- **Currency:** single marketplace → native (US=USD, CA=CAD, UK=GBP, AU=AUD), with a **native↔USD toggle
  for CA/UK/AU**; **All → USD**. USD conversion uses a **per-month rate per currency** (monthly average of
  Frankfurter/ECB daily rates, in `fx_monthly_rates`, populated by `sync.fx_rates`); the fixed book rates
  in `app/pnl.py` are only a fallback. CA/AU `cog` is stored in USD and converted like any USD value —
  never double-converted. See `reference/data/currency_selector_fx.md`.
- **Ad Spend** comes from `ad_spend_daily` (not in `pnl_monthly`).
- **Custom date range:** the date-range picker (two native date inputs + Apply/Clear) switches the
  grid to a single-column P&L for any day range, served from `pnl_daily` via `GET /pnl?start&end`.
  Clear returns to the month columns. See `reference/data/custom_date_ranges.md`.
- An inline note flags that the Operational Fees / Reimbursements **split** is provisional (their
  combined total is reconciled).

Correct Amazon figures only — no in-UI divergence explanations (those live in the probe doc §8).

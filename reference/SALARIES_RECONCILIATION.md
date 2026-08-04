# Plan: Salaries + Contribution rows on the ALL P&L dashboard

## Context

The P&L dashboard currently ends its per-column math at four gross-profit rows
(`Gross Profit Monthly/Daily (with/no reimbursement)`). The business wants to see
**contribution after payroll** — i.e. gross profit minus company salaries — directly
on the dashboard. Salaries are a single company-wide cost, so these rows belong on the
**ALL** marketplace view only (already always USD), not on the per-marketplace tabs.

Salary levels change over the year and must be editable without a redeploy, so we add a
DB-backed override table plus a small write API and an in-page gear/dialog editor. Code
defaults seed the known schedule:

| Period (2026)     | Daily salary (USD) |
|-------------------|--------------------|
| Jan               | 887                |
| Feb – Apr         | 677                |
| May – end of year | 660                |

The figures are **daily** amounts (shown as-is in "Salaries Daily"); monthly = daily × days-in-month.

## New rows (in order, appended after `Gross Profit Daily (no reimbursement)`)

Let `days = period_days[p]`, `sal_d = salary daily for the period`,
`with_reimb[p]` / `no_reimb[p]` = existing monthly gross-profit maps in `_finalize`.

1. **Salaries Daily** = `sal_d`
2. **Daily Contribution (with reimbursement)** = `no_reimb[p]/days − sal_d + reimb[p]/days`  (≡ `with_reimb[p]/days − sal_d`)
3. **Monthly Contribution (with reimbursement)** = row 2 × `days`  (≡ `with_reimb[p] − sal_d·days`)
4. **Daily Contribution (no reimbursement)** = `no_reimb[p]/days − sal_d`
5. **Monthly Contribution (no reimbursement)** = row 4 × `days`  (≡ `no_reimb[p] − sal_d·days`)

Daily-row **Total** column follows the existing convention (grand monthly-equivalent total ÷ `total_days`);
monthly-row Total = sum of the period values. These 5 rows are emitted **only when `alias == "ALL"`**.

## Backend

All in `backend/app/pnl.py`, `backend/app/main.py`, and one new Alembic migration.

### 1. Override table (new migration)

New file under `backend/db/migrations/versions/`, `down_revision = "b8c9d0e1f2a3"` (current head).
Mirror the shape of `fx_monthly_rates` but global (no marketplace_id — company-wide):

```sql
CREATE TABLE salary_override (
    year_month   char(7) PRIMARY KEY,       -- 'YYYY-MM'
    daily_amount numeric(18,4) NOT NULL,    -- USD daily salary
    updated_at   timestamptz NOT NULL DEFAULT now()
);
```

### 2. Default schedule + resolver (`pnl.py`)

Add near the other module constants:

```python
def _default_daily_salary(ym: str) -> Decimal:   # USD, company-wide
    y, m = (int(x) for x in ym.split("-"))
    if (y, m) == (2026, 1): return Decimal("887")
    if y == 2026 and 2 <= m <= 4: return Decimal("677")
    return Decimal("660")   # May 2026 onward (catch-all)
```

Add a loader mirroring `_load_monthly_rates` (pnl.py:159): read all rows from
`salary_override` into `{year_month: Decimal(daily_amount)}`.

Add a resolver that, given the loader dict + a `ym`, returns the override if present
else `_default_daily_salary(ym)`.

### 3. Feed salaries into `_finalize`

Compute a `salary_month` map per period and pass it as a new `_finalize` param
(`salary_month: dict[str, Decimal] | None`; `None` ⇒ skip the 5 rows). Unifies both views:

- **`assemble`** (pnl.py:353) — only when `alias == "ALL"`: build the override dict, then
  `salary_month[m] = daily_salary(m) * period_days[m]` for each `SETTLED_MONTHS`. Else `None`.
- **`assemble_range`** (pnl.py:390) — only when `alias == "ALL"`: day-weight like the FX loop
  (pnl.py:426): `salary_month["range"] = Σ over each day in [start,end] of daily_salary(day's YYYY-MM)`.
  Else `None`.

In `_finalize` (after the 4 GP rows at pnl.py:330, before the FX block at 332), when
`salary_month is not None` derive `sal_d[p] = salary_month[p]/period_days[p]` and append the
5 rows using the existing `_monthly_row` / `_daily_row` helpers (extend `_daily_row` to accept a
precomputed monthly-equivalent map, which it already effectively does). Reuse `q()` for cents.
No `net`/`rate`/`children` flags — these render as plain rows via the generic frontend path.

Add row-label constants next to `GP_*` (pnl.py:54): `SAL_DAILY`, `CONTRIB_DAILY_WITH`,
`CONTRIB_MONTHLY_WITH`, `CONTRIB_DAILY_NO`, `CONTRIB_MONTHLY_NO`.

### 4. Write + read API (`main.py`)

The `/pnl` endpoint is read-only + password-guarded (`require_password`, main.py:47). Add two
routes reusing that dependency and `_db_url()`:

- `GET /salaries` → for each `SETTLED_MONTHS`: `{year_month, daily_amount (effective), is_override}`.
  Populates the dialog.
- `PUT /salaries` → body `{year_month, daily_amount}`; `INSERT … ON CONFLICT (year_month) DO UPDATE`
  into `salary_override`. Optionally `DELETE /salaries/{year_month}` to reset to default.

Validate `year_month` format and non-negative amount.

## Frontend (`frontend/app/page.jsx`)

The renderer is fully generic (page.jsx:250) — the 5 rows appear automatically once the API
emits them, no row-specific JSX. Only two additions:

1. **Gear button** — show only when `marketplace === "ALL"`. Place in the existing toolbar row
   near the marketplace/currency nav (page.jsx:158-191) or the date-range form (195-226). A small
   `⚙` button toggling `settingsOpen` state.

2. **Salary dialog** — new component, built from scratch with Tailwind + `useState` (no dialog lib
   exists; model the centered-card style on the password gate at page.jsx:110-137, add a
   fixed backdrop for a true overlay). On open, `GET /salaries` (send `X-Dashboard-Password`
   header like the existing fetch at page.jsx:59) and render one editable numeric input per
   month showing the effective daily salary, with a per-row "reset to default" affordance.
   Save issues `PUT /salaries` per changed month, closes, and re-triggers the `/pnl` fetch
   (e.g. bump a `refreshKey` in the effect's dependency list at page.jsx:98) so the rows update.

Keep the same `API_BASE`, password header, and 401 handling already in the file.

## Files to modify

- `backend/db/migrations/versions/<new>_salary_override.py` — new table (head `b8c9d0e1f2a3`)
- `backend/app/pnl.py` — default schedule, override loader/resolver, `_finalize` param + 5 rows, `assemble`/`assemble_range` wiring
- `backend/app/main.py` — `GET`/`PUT` (`/salaries`) endpoints reusing `require_password`
- `frontend/app/page.jsx` — gear button (ALL only) + salary dialog + refetch

## Verification

1. **Migration**: run the Alembic upgrade; confirm `salary_override` exists and head advances.
2. **Backend math** (ALL, USD): `GET /pnl?marketplace=ALL&currency=usd`. Check the 5 new rows
   appear after `Gross Profit Daily (no reimbursement)`, Salaries Daily = 887 (Jan) / 677 (Feb–Apr)
   / 660 (May–Jun), and per column verify:
   `Monthly Contribution (no reimb) == Gross Profit Monthly (no reimb) − 887·daysInMonth` (Jan), and
   `Monthly Contribution (with reimb) == Monthly Contribution (no reimb) + Reimbursements` for the month.
   Confirm `Daily × days == Monthly` for both contribution pairs.
3. **Scope**: `GET /pnl?marketplace=US` (and CA/UK/AU) — confirm none of the 5 rows are present.
4. **Range view**: `GET /pnl?marketplace=ALL&start=2026-01-15&end=2026-02-15` — confirm the rows
   appear once, with a day-weighted salary spanning the Jan(887)/Feb(677) boundary.
5. **Override round-trip**: `PUT /salaries {year_month:"2026-03", daily_amount:700}`, refetch `/pnl`,
   confirm March Salaries Daily = 700 and contribution rows shift accordingly; `DELETE` (or reset)
   restores 677.
6. **Frontend**: on the ALL tab, gear appears; open dialog, edit a month, save, and confirm the
   dashboard rows refresh; switch to US and confirm the gear + rows disappear. Run `/run` to drive
   the app and eyeball the new section.

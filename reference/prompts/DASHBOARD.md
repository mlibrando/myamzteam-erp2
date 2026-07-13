# Claude Code Task — v1 P&L dashboard: FastAPI read endpoint + Next.js grid

## Context

Build the v1 P&L dashboard that replaces Elena's manual Sellerise sheet. Month-as-column grid (rows =
P&L line items, columns = months), one marketplace at a time, plus an "All" view in USD. Built against
`reference/data/pnl_dashboard_probe.md` — read it first; it is the contract. Do not re-derive the
mapping; use the probe's verified one.

**Stack (lean, do not add to it):** yarn, Next.js, Tailwind, FastAPI read endpoint. **No Zustand** (two
pieces of UI state — use `useState`). No charts. No writes. No new deps beyond these.

## Decisions locked (from the probe + product calls)

- **Rows (v1):** Sales, COGS, Ad Spend, Selling Fees, Operational Fees, Refunds, Reimbursements from AMZ.
  No Gross Profit / ROAS / Salaries.
- **Two sources:** six rows from `pnl_monthly`; **Ad Spend from `ad_spend_daily`** (sum `total_cost` by
  marketplace/month) — it is NOT in `pnl_monthly`.
- **Currency:** single marketplace → native (US=USD, CA=CAD, UK=GBP, AU=AUD). "All" → USD at Elena's
  fixed book rates (GBP×1.34, CAD×0.71, AUD×0.69), in config, labelled as her book rates.
- **CA/AU cog is stored in USD.** Native view: convert cog USD→native for display (CA ÷0.71, AU ÷0.69).
  All→USD view: convert sales/other native→USD, but **do NOT re-convert CA/AU cog** (already USD —
  double-conversion trap).
- **AU:** show its numbers, no comparison column.
- **No in-UI divergence explanations.** Correct figures only; §8 is a separate talking-points doc.
- **Auth:** single shared password in an env var, checked **server-side in FastAPI**. Never compare the
  password in frontend JS.

## The bucket→row mapping is a WHITELIST (critical)

Map exactly these buckets to rows. **Ignore everything else** — especially the entire `passthrough`
bucket. This must be an allow-list, not "sum all buckets minus a blocklist," so a future passthrough
leaf (e.g. another `Transfer.*`) can never leak into a P&L row.

| row | source | sign |
|---|---|---|
| Sales | `pnl_monthly` bucket `chargesObject` (all leaves) | as stored (+) |
| COGS | `pnl_monthly` bucket `cog` | as stored (−) |
| Ad Spend | `ad_spend_daily` sum `total_cost` | (−) for display |
| Selling Fees | `pnl_monthly` buckets `feesObject` + `fbaObject` | as stored (−) |
| Operational Fees | `pnl_monthly` `storageFee` + `expenses` **non-reimbursement** leaves (incl. `FBAReversedReimbursement`, money out) | as stored (−) |
| Refunds | `pnl_monthly` bucket `refundsObject` | as stored (−) |
| Reimbursements from AMZ | `pnl_monthly` `expenses.FBAInventoryReimbursement.*` (money in) | as stored (+) |

- **Never** include `passthrough` (facilitator tax/VAT, `Transfer.FundTransfer`, `Adjustment.Reserve*`,
  `ProductAdsPayment.*`, `Shipment.Promo`). `Transfer.FundTransfer` is a +$100k US-Jan settlement
  movement — a P&L-poisoning leak if included.
- `net` is not stored; the dashboard sums the rows it displays. Define the net row explicitly as
  Sales + COGS + Ad Spend + Selling + Operational + Refunds + Reimbursements (signs as above).

## Step 1 — FastAPI read endpoint

- `GET /pnl?marketplace={US|CA|UK|AU|ALL}` → the month-as-column grid: rows above, columns = settled
  months (Jan–Jun 2026), plus a total column.
- The endpoint does the assembly server-side: whitelist-map `pnl_monthly` buckets, join
  `ad_spend_daily` for Ad Spend, apply the currency rules, compute the net row. Frontend receives
  display-ready numbers + the currency code for the view.
- **`marketplace=ALL`:** convert each marketplace to USD at book rates (cog already USD → not
  re-converted), then sum per row per month. Return currency USD.
- **Auth:** require the shared password (header or cookie); compare against the env var **in FastAPI**.
  Return 401 if absent/wrong. Do not embed the password anywhere client-readable.
- Keep it one endpoint + a small assembly module. No ORM ceremony if raw SQL is clearer; no per-row
  API round-trips.

## Step 2 — Next.js grid

- Marketplace selector (US/CA/UK/AU/All) and — if multiple months — it shows all settled months as
  columns at once (like Elena's sheet), not a month picker. Total column on the right.
- Rows in Elena's order: Sales, COGS, Ad Spend, Selling Fees, Operational Fees, Refunds, Reimbursements,
  then a Net row.
- **Currency formatting is correctness, not cosmetics:** render the right symbol and decimals for the
  view's currency (£/$/CA$/A$). Never show a GBP figure with a $ sign. Negative costs shown as Elena's
  sheet does (parenthesised or −, your call, consistent).
- Provisional note on **Operational Fees + Reimbursements**: a small inline note that the split between
  these two rows is pending review, but their **combined** total is reconciled. Do not make it alarming;
  the numbers are trustworthy, only the split boundary is provisional.
- Password entry: a simple gate (one field) that stores the password for the session and sends it to the
  API. No user accounts.
- Tailwind only; no component library. A clean, legible table — this replaces a spreadsheet, so
  readability over decoration.

## Step 3 — Verify

- `/pnl?marketplace=US` reproduces the probe's US figures (Sales, COGS, Selling, Refunds from
  `pnl_monthly`; Ad Spend 31,368.66 from `ad_spend_daily`; the whitelisted buckets only).
- `Transfer.FundTransfer` and no `passthrough` leaf appears in any row or the net.
- CA/AU native view: cog converted to native, coherent single-currency column.
- ALL view: sums in USD, CA/AU cog not double-converted; spot-check one row/month by hand.
- Wrong/absent password → 401; correct password → data. Password never present in any client bundle or
  network payload readable before auth.
- No writes anywhere (read-only endpoint; no `pnl_monthly` / `ad_spend_daily` / snapshot mutation).

## Guardrails

- Whitelist mapping only — never "sum all buckets." `passthrough` never enters a row.
- Currency: native per marketplace; USD only for ALL; CA/AU cog never double-converted.
- Auth compared server-side only. No password in frontend code.
- No Zustand, no charts, no write paths, no deps beyond yarn/Next/Tailwind/FastAPI.
- Do not touch reconciliation math, `pnl_monthly`, `ad_spend_daily`, buckets, or the pipeline.
- Read the probe doc; use its mapping verbatim. Do not re-derive or "improve" it.

## Definition of done

- `GET /pnl` returns the month-as-column grid per marketplace and for ALL (USD), assembled server-side
  with the whitelist mapping, Ad Spend from `ad_spend_daily`, and the currency rules; password checked
  in FastAPI.
- Next.js grid renders it in Elena's row order with correct per-currency formatting, a marketplace
  selector, all settled months as columns, a total column, a net row, and the provisional split note.
- Verified: US matches the probe; no passthrough/FundTransfer leak; native cog converted; ALL sums in
  USD without double-conversion; auth gates server-side.
- Lean stack only; no writes; reconciliation untouched.
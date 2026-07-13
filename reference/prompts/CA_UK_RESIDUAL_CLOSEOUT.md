# Claude Code Task — Complete CA/UK ads, then diagnose the CA residual (verify before accepting)

## Context

CA + UK rollout is live and gated (`reference/data/rollout_ca_uk_results.md`). UK reconciles
cleanly; US baseline is untouched. Two things are NOT yet closed and the write-up files them as
follow-ups — one of them is actually an unfinished diagnosis.

1. **CA/UK May+Jun ads aren't persisted** (raw CSVs cover only Jan–Apr), so May/Jun net includes
   a `adExpenses=0` overstatement.
2. **CA carries a same-signed post-ads residual** on the ads-complete months (Jan–Apr):
   −$323, −$532, −$422, −$269 — negative every month, ~3–4% of CA net (CA is ~1/10 US scale).
   UK's equivalent (−$297, −$316, −$112, −$240) is small/mixed = accepted drift; **CA's is
   flat-negative, which is the exact fingerprint that turned out to be a real cog mechanism twice
   on US, not drift.** The write-up labels it "likely cog fine-tuning" without decomposing it —
   the same "almost certainly X" shortcut this project has caught before.

These interact: CA's Σ Jan–Jun (−$1,096) is smaller than Σ Jan–Apr (−$1,546) because the
ads-missing May/Jun months are positive and partially cancel the real negative residual. **Two
errors offsetting.** So the ads must be completed first, or the CA residual can't be judged.

## Operating rules

- **Complete the data, then diagnose, then decide.** Do not accept the CA residual as "drift"
  without a per-bucket decomposition — its shape says otherwise.
- Minimalist: finish the existing ads pull per marketplace; the diagnosis reuses the US
  per-bucket decomposition method. No new engine work.
- Verify with numbers; state the CA verdict as what the decomposition shows.

## Step 1 — Complete CA/UK May+Jun ads (prerequisite, not a follow-up)

- Run the full-year `ads_spend.py` per marketplace (CA, UK) so May and Jun `totalCost` is
  persisted with the same `as_of` handling as US/Jan–Apr. Filter `budget_currency` per marketplace
  (CAD/GBP).
- Re-run both reports. Confirm UK May/Jun move from +$415/+$420 toward the small near-zero band —
  if UK now reconciles across all six months, UK is done.

## Step 2 — Decompose the CA residual (the actual diagnosis)

- Pick a CA settled month where ads is now complete and exact (verify ads Δ ≈ 0 first, so ads is
  removed as a variable — the US March trick). Decompose CA net Δ into per-bucket contributions
  (`chargesObject` by sub-line, `feesObject`, `fbaObject`, `refundsObject`, `storageFee`, `cog`,
  `adExpenses`, derived `salesTaxes`). Assert they sum to the measured net Δ (sanity residual ≈ 0).
- Repeat across CA Jan–Jun. Identify the bucket carrying the same-signed residual. If it's `cog`
  (as the shape suggests), that's the lead.

## Step 3 — If cog: test the mechanism (don't assume the basis fixed it)

Gate 2 chose CA's refund-COGS *basis* (posted-date), but choosing the winning basis does NOT prove
refund COGS is netted correctly on that basis. Test the same failure modes US had:

- Is CA netting **all refund statuses** (RELEASED + DEFERRED_RELEASED + DEFERRED as appropriate),
  or only a subset? Re-run the netting with the full status set and check whether the flat residual
  collapses (mirror the US all-status finding).
- Is the returned-unit basis right — `refunded_units × cog_per_sku` on the CA COGS sheet, joined on
  the same SKU key? Check for a units mismatch or a CA SKU with no cog rate (log, don't zero).
- If a change collapses the same-signed residual toward zero across settled CA months, commit it;
  if it doesn't, the residual isn't refund-COGS netting — report the actual bucket.

## Step 4 — Decide, per the evidence

- If the CA residual decomposes to a **fixable mechanism** (cog netting/units) → fix, re-run,
  confirm CA settled months reach the small mixed-sign drift band UK/US show.
- If it decomposes to **mixed-sign small per-bucket drift** (like UK) → accept as CA restatement
  drift, documented per-cause, and label it correctly (NOT "cog fine-tuning" hand-wave).
- Either way: CA's residual must end up **named**, not filed as a vague follow-up.

## Step 5 — Per-marketplace drift bands (close the monitoring gap)

- Derive CA and UK drift bands from **their own** observed drift, not copied from US. US dollar
  bands are ~10× too loose for these markets and would make the guards blind. Add
  `DRIFT_BANDS_BY_MARKETPLACE` (both vs-Sellerise and vs-prior-pull). Verify each marketplace's
  current clean state reads 0 INVESTIGATE, and that a perturbation fires (same acceptance test as US).

## Guardrails

- Do not accept the CA same-signed residual without the Step 2 decomposition — flat-signed is the
  systematic-bug fingerprint, not drift.
- Do not judge any month whose ads aren't persisted — complete ads first (Step 1).
- Per-marketplace bands from per-marketplace drift; never copy US dollar bands.
- Do not touch US or AU. Do not widen tolerance to make CA "pass."

## Definition of done

- CA/UK May+Jun ads persisted; both reports re-run across all six months.
- UK confirmed reconciled across all months (or its residual named).
- CA residual decomposed per bucket and **named**: either fixed (with the mechanism identified and
  the flat residual collapsed) or accepted as evidenced mixed-sign drift — not "likely cog
  fine-tuning."
- Per-marketplace drift bands added and verified (0 INVESTIGATE clean; perturbation fires).
- No US/AU change; no tolerance widened.
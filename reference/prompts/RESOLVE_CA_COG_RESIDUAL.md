# Claude Code Task — Resolve the CA cog residual: FX-derived cost bug vs true governance drift

> **SUPERSEDED PREMISE — the fix this brief produced is correct; its stated reason is not.**
> Body left as written. See [`../data/decisions_audit.md`](../data/decisions_audit.md).
>
> This brief frames CA's `US_cog × 1.35` as evidence the sheet holds "mechanically derived" values
> rather than "true CA-sourced per-unit costs". That framing is refuted. **The CA sheet's cost column
> is denominated in CAD**, and 1.350 is the CAD/USD rate — a correct conversion, not a fake
> multiplier. (Corroboration: the CA *retail* column is US × 1.1440, a different multiplier. One
> mechanical FX scaling would have moved both columns by the same factor.)
>
> `MARKETPLACE_COG_SOURCE_OVERRIDE` (CA→US) works because it puts a **USD cog against Sellerise-CA's
> USD `cog` field** — Sellerise-CA reports revenue in CAD but `cog` in USD. It has nothing to do with
> the CA sheet's quality. **Do not remove the override when "real CA cost data lands"**; that would
> re-introduce a +$2,425.58 / +29.1 % cog error. Real CAD-sourced costs would make the override *more*
> necessary, not less.

## Context

CA rollout reconciles except for a same-signed positive `cog` residual (+$258 to +$632/month,
~3–4% of CA net). Step 3 thoroughly ruled out a *pipeline* mechanism (refund status filtering,
all basis combos, missing SKUs). Step 4 then named it "per-SKU cog value drift — data governance,
not fixable."

**That verdict contradicts its own evidence and must be re-tested before it's accepted.** Step 4
reports two facts that can't coexist under the stated conclusion:

1. CA cog = **US cog × 1.35** (a currency conversion applied at workbook load), and
2. the Sellerise/ours ratio **varies 0.68–0.85 month to month**.

If CA costs are a *fixed 1.35 multiple of US*, then per-SKU values are **not independently
drifting** — they're mechanically derived. So "per-SKU value drift" cannot be the cause. A
month-to-month ratio swing with a *fixed* input multiplier is the signature of a **product-mix
effect**: the ratio moves because the SKU mix changes each month, while the per-SKU error is a
consistent function of the SKU. That points at a **fixable cost-basis bug** (US×1.35 is the wrong
CA cost; Sellerise uses true CA-sourced per-unit costs), not unfixable governance noise.

This is the same "plausible label before the discriminating test" pattern caught earlier in this
project. Run the test.

## Operating rules

- **Diagnose, don't fix yet.** Determine the mechanism first; the fix depends on which it is.
- Verify with numbers over data in hand (CA COGS sheet, CA transactions, Sellerise CA cog per month).
- State the verdict as what the SKU-vs-month structure shows.

## Step 1 — Confirm how CA per-SKU costs are actually produced

- Inspect the CA COGS workbook load path. Is the CA per-SKU cost genuinely `US_cog × 1.35`
  (a hardcoded/derived FX multiplier), or does the CA sheet carry independently-entered CA costs?
  Report exactly how each CA SKU's cost is set. This alone may settle it: if CA costs are a fixed
  multiple of US, "per-SKU value drift" is false by construction.

## Step 2 — Decompose the error: SKU-structured vs month-random (the discriminator)

- For each settled CA month, compute per-SKU cog contribution (units_sold × our_cost) and, where
  derivable, the implied Sellerise per-unit cost (Sellerise monthly cog attributed back, or via any
  per-SKU Sellerise detail available). Compute per-SKU error = ours − implied-theirs.
- Split the variance two ways:
  - **By SKU:** is each SKU's error a consistent %/$ offset across months (SKU X always ~+Y%)?
  - **By month:** is the error random per SKU per month with no SKU structure?
- If the error is a consistent per-SKU offset and the monthly ratio swing (0.68–0.85) is explained
  by **which SKUs sold** (mix), the cause is the cost basis → **FIXABLE**. If the error is
  structureless per SKU per month → governance, → accept.

## Step 3 — If cost-basis (fixable): quantify the correct CA costs

- The likely bug: US×1.35 approximates CA cost but the true per-unit CA costs differ per SKU
  (real sourcing, duties, freight — not a flat FX). Check whether replacing the derived CA costs
  with true CA-sourced per-unit costs (if present on the CA sheet, or obtainable) collapses the
  same-signed residual across settled months.
- Do NOT apply a new flat multiplier to "close" it — that would just be a different wrong constant.
  The test is whether *real per-SKU CA costs* reconcile; if the true costs aren't available, the
  finding is "CA COGS source data is US-derived and needs real CA costs," which is a data task, not
  a pipeline shrug.

## Step 4 — Decide and, if fixed, tighten the band

- **Fixable cost-basis:** correct the CA cost source, re-run, confirm the CA cog residual collapses
  toward the small mixed-sign drift band UK/US show. **Then shrink the CA vs-Sellerise cog band**
  from $1,000 — it is currently sized to absorb this unexplained residual, exactly what the
  guardrails warn against. A band sized to hide an unfixed problem must not survive the fix.
- **Genuinely structureless:** accept as CA COGS governance drift, but label it precisely with the
  SKU-vs-month evidence (not "value drift" hand-wave), and note the $1,000 band is a known
  compensation for an accepted data-quality gap, flagged for revisit if CA cost data improves.

## Guardrails

- Do not accept "per-SKU value drift / governance" without the Step 2 SKU-vs-month split — the
  ×1.35 evidence actively points the other way.
- Do not close by applying a new flat multiplier; only real per-SKU CA costs count as a fix.
- The wide CA cog band is provisional — it must shrink if the residual is fixed, not persist.
- Do not touch US or AU; do not widen any tolerance.

## Definition of done

- Exact CA per-SKU cost derivation reported (Step 1) — settles whether "value drift" is even possible.
- Per-SKU error split by SKU vs by month; monthly ratio swing explained by mix or shown random.
- Verdict: **fixable cost-basis** (with the corrected-cost re-run and the CA cog band tightened) OR
  **accepted governance drift** (with SKU-vs-month evidence and the band flagged as compensation).
- CA residual ends **correctly named**, not labeled with a conclusion its own evidence contradicts.
- No US/AU change; no tolerance widened.
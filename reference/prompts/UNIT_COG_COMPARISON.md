# Claude Code Task — Back out Sellerise's implied per-SKU Unit COG and compare to the workbook

## Context

Sellerise computes COGS as `(units_sold − units_refunded) × unit_COG` — a single per-unit cost per
SKU, no freight/duty buildup. This matches our pipeline's netting exactly, so any UK/CA COGS
residual is **purely a per-unit cost-value disagreement** between our workbook and Sellerise's
`unit_COG`. This task quantifies that gap per SKU so the DMS gets exact deltas, not "~5–15% high."

## Task

For UK and CA (and US as a control):

1. **Back out Sellerise's implied unit COG per SKU.** For each SKU with sufficient data, use
   Sellerise's monthly `cog` and our net units `(units_sold − units_refunded)` for that SKU/month to
   solve `implied_unit_cog = sellerise_cog / net_units`. Where a month's `cog` is a marketplace total
   rather than per-SKU, solve across months with a small least-squares fit on per-SKU net units;
   prefer SKUs/months where attribution is clean and flag low-confidence SKUs.
2. **Compare to the workbook.** Join implied Sellerise `unit_COG` against our workbook per-SKU COGS.
   Emit: `SKU | ASIN | product | workbook_unit_cog | sellerise_implied_unit_cog | Δ | Δ%`.
3. **Rank by dollar impact** = `|Δ| × net_units` per SKU, so the DMS sees which SKUs actually move the
   residual, not just the biggest percentages.

## Sanity check — US control (report this)

- US already reconciles, so US SKUs should show near-zero implied-vs-workbook Δ. If US shows large Δ,
  the back-out method is flawed — fix the method before trusting the UK/CA numbers.

## Guardrails

- Diagnostic only. **Do not edit the workbook or any COGS value.** The output tells the DMS which
  numbers disagree; the DMS decides which is authoritative.
- Flag per-SKU results as low-confidence where net units are tiny (a few refunds swing implied cost
  wildly).
- No US/CA/AU number changed; no pipeline logic changed.

## Definition of done

- `reference/data/unit_cog_comparison.md`: per-SKU `workbook vs Sellerise-implied unit_COG` table for
  UK and CA, ranked by dollar impact, with US as a validating control (near-zero Δ).
- Low-confidence SKUs marked. No values edited.
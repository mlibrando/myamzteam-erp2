# Claude Code Task — Correct superseded doc conclusions, then re-run the decisions audit

## Context

The first decisions audit was correct in method and produced three real blockers (missing ads loader,
`sync/__main__.py` KeyError, stale `pnl_monthly` CA cog). It also faithfully reported two doc
conclusions that have since been **overturned by evidence the docs never saw.** The docs' *measurements*
are right; two of their *interpretations* are wrong. Fix the interpretations, keep the measurements,
then re-run the audit.

**Do not delete any reference doc.** They hold the measurements and the reasoning history. Mark
superseded conclusions in place.

## Ground truth (authoritative — established outside the docs)

1. **UK COGS: the workbook is CORRECT; Sellerise is UNDERSTATED.**
   - Elena validated the UK sheet against the **component cost build-up**: ABDB £78.53, GMAKER-3
     £30.94, MBUKB1 £96.06 — all tie out exactly. Sellerise understates **ABDB by ~28%** and
     **MBUKB1 by ~2%**; it matches only on GMAKER-3.
   - `unit_cog_comparison.md:239` measured this correctly ("pipeline HIGH; workbook costs
     systematically above Sellerise") but **concluded the wrong direction** — it filed it as a
     data-governance action on our side with "no pipeline fix."
   - "Workbook above Sellerise" and "Sellerise understates the workbook" are the **same measurement**.
     A comparison cannot say which side is right; the build-up table can, and it says the sheet is.
   - **Correct classification: a Sellerise-side data defect (`KNOWN_TARGET_DEFECT`), like AU's
     Sellerboard GST omission. Do NOT edit the UK workbook. Do NOT "fix" our cog to match Sellerise.**

2. **AU COGS workbook is USD-magnitude, despite an AUD label.** Established three ways: AU retail
   column 133.97 (US price 130.95; in AUD it would be ~195); AU cog 30.99 ≈ Sellerise-US 30.76 USD;
   AU margin 77% == US margin 77%. `MARKETPLACE_COG_CURRENCY[AU] = "USD"` is correct. Sellerboard AU
   reports USD (confirmed in its settings). The pipeline holds AUD.

## Step 1 — Mark superseded conclusions in place (do not rewrite bodies, do not delete)

Add a short header to each affected doc noting the superseding evidence and pointing to it:

- `unit_cog_comparison.md` — its UK conclusion is inverted (see Ground truth 1). Keep the numbers.
- Any doc asserting Sellerboard `netProfit` uses `salesCosts` — it uses **`productCosts`**.
- Any doc stating the inventory-loss gap is **$845** — it is **−$705.39**.
- Any doc framing CA's ×1.35 as a "fake FX multiplier" — it is a **genuine CAD markup**; the override
  works because it puts USD cog against Sellerise-CA's USD cog.
- Any doc carrying the "Sellerboard entered raw AUD into a USD field" theory — refuted.
- `PLAN.md` — prepend: `> STALE — predates the CA/UK/AU rollout. Authoritative: reference/data
  findings + the code.`

Also move the ~20 prompt `.md` files out of the repo root into `reference/prompts/`. They are history,
not instructions. Nothing else in the root but `backend/`, `reference/`, `PLAN.md`, `README.md`, configs.

## Step 2 — Fix the one landmine comment (the only code change permitted)

`config.py:161-163` instructs a future maintainer to remove the CA cog override once real CA cost data
lands. Following it re-introduces the full **+$2,425.58 / +29.1%** error. The override exists to put a
**USD cog against Sellerise-CA's USD cog** — it has nothing to do with the CA sheet's quality (the CA
sheet is CAD, US × 1.350, a correct markup).

Replace the comment with what actually breaks if it is removed. **Change no behavior.**

## Step 3 — Re-run the decisions audit against corrected sources

Read-only, same as before. Re-emit `reference/data/decisions_audit.md` with:

- The marketplace × decision table (target, revenue basis, refund dollars basis, refund-COGS basis,
  COGS sheet + **actual** currency, cog source override, pipeline/target currency, FX handling, tax
  families, marketplace-specific mappings, ads, bands + restatement profile, known target-side defects,
  accepted residuals). Every cell: wired value + evidence pointer, or `UNVERIFIED`.
- **Report what the code does, not what a doc claims.** Where they still disagree, that is a finding.
- Carry forward the three blockers already found (ads loader not in repo; `__main__.py:94`
  `agg_stats["groups"]` KeyError; stale `pnl_monthly` CA cog at +29.1% with wrong `currency` label).
- Known target-side defects now include: **Sellerise UK understates ABDB ~28% / MBUKB1 ~2%**;
  Sellerboard AU omits GST on Jan storage and counted 1 MCF unit in Jan.
- Open items: **CA's refund-COGS basis was scored against the pre-override cog ($2,596.90, since taken
  to $909.31) — the purchase arm was never recomputed.** UK's FBA −$458 label rests on a rate-signature
  inference; the only pull-to-pull evidence is a 36-second re-pull, which cannot observe weeks-scale
  restatement.

## Guardrails

- **Delete no reference doc.** Superseded conclusions get a header, not a grave.
- Read-only except Step 1 headers, the file moves, and the Step 2 comment. **No behavior changes.**
- Do not edit the UK workbook or change UK cog to match Sellerise.
- Do not run the committed `ads_spend.py` against CA/UK/AU — it would DELETE reconciled rows.
- `UNVERIFIED` is a valid cell. Do not mark anything verified without a test behind it.

## Definition of done

- Superseded conclusions headered in place; prompts moved to `reference/prompts/`; `PLAN.md` marked stale.
- `config.py` override comment replaced with what breaks if removed; no behavior changed.
- `decisions_audit.md` re-emitted against corrected sources, with UK reclassified as a Sellerise-side
  defect and AU's USD workbook currency recorded.
- Three blockers restated; CA refund-COGS basis and UK FBA label listed as open.
- `git diff -- backend/` shows only the `config.py` comment.
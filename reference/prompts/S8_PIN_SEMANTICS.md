# Claude Code Task — S8: make pinned defects survive live ingestion

## Context

`TARGET_DEFECTS` pins a Δ measured against a **frozen** Sellerise/Sellerboard snapshot and a **frozen**
Amazon pull. But Phase 1 ingests. New transactions can move a pinned Δ on a correct pipeline.

Observed live: a UK Refund posted 4 July, on an order purchased 18 January. UK's refund-COGS basis is
**purchase**, so it nets that unit back into January's cog and moves the pinned Jan cog Δ from **242.84
→ 236.14** — inside the ±25 tolerance by only **£18.30**. Had the SKU been ABDB (£78.53) instead of
4C-76GT-VAWZ (£6.70), **the pinned cell would have fired INVESTIGATE on a correct pipeline, correct
ingestion, and an unchanged target defect.** A false positive on a coin flip.

Before the cron runs unattended, fix this. An unattended job that goes red on a legitimate refund is
worse than no job.

## Operating rules

- **Simplicity.** This is a classification change plus one status and a documented protocol. No new
  abstraction layer, no registry framework, no refactor of `classify()` beyond what's needed.
- **The pin must still pin.** Whatever changes, a defect that genuinely moves must still fire
  `INVESTIGATE`, and a defect the target *fixes* (Δ → 0) must still fire. No band widening.
- Change no reconciliation math, attribution, bucket maps, or reported numbers.

## Step 1 — Classify each pinned defect: rate or content

Two kinds, and they behave differently under ingestion:

- **Rate defect** — the target derives a per-unit value wrong. Its dollar Δ **scales with monthly
  volume**, so a dollar pin needs a new entry every month and moves whenever units move.
  → **Pin the rate, not the dollars.** Ingestion-invariant.
  - *UK fbaObject (5 cells):* Sellerise books **£0.195/unit** where Amazon bills **£3.374/unit** for
    GMAKER-3, and books nothing at all for it in five of six months. The Δ tracks GMAKER-3's unit share
    (10%→25%) exactly. This is a rate defect.
  - *UK cog (4 cells):* Sellerise's per-SKU costs sit below the workbook's. Also per-unit derived.
    Classify by the same test.

- **Content defect** — the target includes or omits specific *items*. Its Δ is a fixed dollar amount
  tied to those items, not to volume.
  → **Pin the Δ**, and re-measure when ingestion legitimately changes the underlying items.
  - *AU Jan storage (−52.75):* Sellerboard omits GST on one line in one month. Fixed dollars.
  - *AU Jan MCF unit:* Sellerboard counted exactly one MCF unit. Fixed items (cog −86.71,
    commission −30.07, FBA −30.27).

Decide each of the 9 entries by the test — **does the Δ scale with units, or is it a fixed set of
items?** Report the classification with its evidence. Don't guess; the UK FBA case is already proven.

## Step 2 — Pin rate defects on the rate

For rate-classified cells, the registry entry stores the **expected per-unit defect** (e.g.
Sellerise ≈ £0.195/unit vs Amazon £3.374/unit for GMAKER-3), and `classify()` compares the *implied
per-unit rate* rather than the dollar Δ. Tolerance is a tight band on the rate.

Why this is the simple option, not the clever one: it removes the "new entry every settled month"
maintenance the last task flagged, **and** it is immune to a refund landing in a prior month — the
dollar Δ moves, the rate does not.

Keep it minimal: the units are already computed for the bucket. No new tables, no new queries.

## Step 3 — Content defects: add `DEFECT_REMEASURED`

For content-classified cells, the Δ is legitimately mobile when ingestion adds/removes items.

- If a pinned Δ moves **and the movement is fully explained by newly-ingested transactions on that
  cell**, report `DEFECT_REMEASURED` (loud in the report, with the old and new Δ and the transactions
  that explain it) and update the registry entry to the new measured Δ.
- If a pinned Δ moves and ingestion **does not** explain it → `INVESTIGATE`, unchanged.
- If the Δ goes to zero → `INVESTIGATE` (the target fixed its bug; delete the entry). Unchanged.

Keep the "explained by ingestion" test simple: the delta in that cell's contributing transactions since
the pin's `measured_at` accounts for the delta in Δ, within the existing tolerance.

## Step 4 — Write down the ingest protocol

Short, in the audit doc. Ingesting is a **deliberate act**, not a side effect:

- Phase 1 (ingest) and the guards are separate operations. A verification/report run must not ingest.
- Order: ingest → reconcile → guards. A `DEFECT_REMEASURED` on the first guarded run after an ingest is
  expected; on a run with no ingest it is a bug.
- Record `measured_at` on every registry entry so "moved since the pin" is answerable.

## Step 5 — Verify

- Replay the observed case: the UK Jan refund (4 July posting, 18 Jan purchase, SKU 4C-76GT-VAWZ). Under
  rate-pinning, the UK cog/FBA cells must **not** move. Confirm.
- Adversarial: substitute ABDB (£78.53) for the refunded SKU. Under the old dollar pin this fires
  INVESTIGATE; under the new scheme it must not.
- The pin still has teeth: perturb the *rate* beyond tolerance → `INVESTIGATE`. Perturb a content
  defect's Δ with no explaining transactions → `INVESTIGATE`. Target fixes the defect (Δ → 0) →
  `INVESTIGATE`. An unregistered cell at the same Δ → still fires.
- `fbaObject × 1.20` and `cog × 1.20` perturbations still fire on all marketplaces.
- All four reports byte-identical except statuses; exit codes unchanged (US 1, CA/UK/AU 0).

## Guardrails

- No band widened. Rate tolerance is tight and derived from observed rate stability, not from the
  defect's size.
- `DEFECT_REMEASURED` must never fire on a run that didn't ingest. If it does, that's a bug.
- Do not re-measure a defect silently — it is reported loudly, with the explaining transactions.
- No changes to reconciliation math, attribution, bucket maps, schema, or `aggregate_marketplace`.
- Do not run the pipeline's Phase 1 during verification (hold `--start` past the 48h boundary, as the
  last task did).

## Definition of done

- Each of the 9 pinned cells classified **rate** or **content**, with evidence.
- Rate defects pinned on the per-unit rate; no per-month registry entry needed; the UK Jan refund case
  no longer moves them.
- `DEFECT_REMEASURED` added for content defects, fires only when ingestion explains the movement, and
  reports old Δ, new Δ, and the explaining transactions.
- Ingest protocol written down; `measured_at` recorded per entry.
- All teeth tests pass (rate perturbation, unexplained content move, Δ→0, unregistered cell, ×1.20).
- No reported number moves; exit codes unchanged.
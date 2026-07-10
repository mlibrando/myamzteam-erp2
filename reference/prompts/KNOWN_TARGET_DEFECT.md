# Claude Code Task — Fix UK cog currency (S7) + add KNOWN_TARGET_DEFECT status (S6)

## Context

Two audit findings, both small, neither touching reconciliation math.

**S7 — UK cog currency is mislabeled.** `config.py:64` declares UK cog currency `USD`, asserted from a
numeric coincidence (30.94 ≈ US 30.76). Now settled: **CA and UK workbooks are in native currency, and
Sellerise reports in native currency too.** UK sheet is **GBP** (£78.53 / £30.94 / £96.06). Margin
coherence agrees (UK 76.4% vs CA 77.3% / AU 77.3%). Benign today — both sides of the UK comparison share
the denomination — but `cog_needs_fx(UK)` reads this flag. Fix the constant.

(For the record: CA = CAD native, UK = GBP native, AU = **mixed** — cost column USD, retail column AUD,
ratio 1.0075 vs US cost. `MARKETPLACE_COG_CURRENCY[AU] = "USD"` stays correct.)

**S6 — the drift guard has no way to express a known target-side defect.** `_UK_SETTLED_BANDS` sizes
`cog.(scalar)` to $100 "sized to post-workbook-fix," commented "Once the workbook is corrected,
INVESTIGATE goes quiet." **The workbook will never be corrected — it is right; Sellerise is the defective
side.** So 4 UK cells fire forever, and `reconcile.py:1267` gates the exit code on `inv_s == 0`, making
`reconcile --marketplace UK` return **1 permanently with no legitimate remediation.**

The guard can say `WITHIN_DRIFT` / `TRAILING` / `INVESTIGATE`. It cannot say *"this Δ is a known
target-side defect; hold it at its measured magnitude and alarm only if it moves."* AU needs the same
vocabulary for Sellerboard's Jan GST omission and its 1 counted MCF unit.

## Operating rules

- **Simplicity.** One status value, one registry of expected magnitudes, one exit-code change. No new
  abstraction layer, no config framework, no refactor of the band machinery.
- **Do not widen any band.** A `KNOWN_TARGET_DEFECT` that swallows any Δ is just a wider band with a
  nicer name. It must alarm on **movement**, not on presence.
- Do not edit the UK workbook. Do not change UK cog to match Sellerise. Change no reconciliation math.

## Step 1 — S7: correct the UK cog currency constant

- `config.py:64` → UK cog currency = **GBP**.
- Verify `cog_needs_fx()` still resolves correctly for all four marketplaces (no FX for US/CA/UK; AU's
  USD-cost / AUD-pipeline handling unchanged).
- Confirm no reported number moves: US/CA/UK/AU reports must be byte-identical before and after.

## Step 2 — S6: add `KNOWN_TARGET_DEFECT`

Minimal shape — resist elaborating:

- A small registry keyed by `(marketplace, month, bucket, sub_line)` → `{expected_delta, tolerance, note}`.
  Plain dict in the existing bands module; no new file, no new config system.
- Classification order: a cell matching a registry entry **within its tolerance** → `KNOWN_TARGET_DEFECT`.
  Outside tolerance (the defect **moved**) → `INVESTIGATE`. Everything else unchanged.
- Tolerance is a **tight** band around the *measured* magnitude — enough to absorb rounding/restatement,
  not enough to hide a change. This is the whole point: it pins the defect, it doesn't excuse the bucket.
- Exit code gates on `INVESTIGATE` only. `KNOWN_TARGET_DEFECT` is reported loudly in the report (its own
  section, with the note) but does not fail the run.

## Step 3 — Register the three known defects

Each with its evidence note, so a future reader doesn't re-diagnose:

1. **UK cog (4 settled cells)** — Sellerise understates UK per-SKU costs. Elena validated the UK sheet
   against the component build-up (ABDB £78.53, GMAKER-3 £30.94, MBUKB1 £96.06 — all tie out). Measured
   aggregate Δ = **+$1,000.62**. *Note in the registry: the relayed "ABDB 28% / MBUKB1 2%" magnitudes do
   not reconcile with this aggregate (28% on ABDB alone implies +$2,484.69); Sellerise exposes only
   monthly aggregate cog, so per-SKU cannot be confirmed from this repo. The classification stands on the
   build-up table; the magnitude is open with Elena.* Register the **measured** Δ, not the relayed 28%.
2. **AU Jan storage (−52.75)** — Sellerboard omits GST from that one line in that one month. Amazon did
   charge it (`ServiceFee.Tax` 77.40 ≈ 10% × 779.54). Arrears hypothesis refuted structurally (one-month
   shift fits 8× worse: Σ|Δ| 535.54 vs 64.17).
3. **AU Jan MCF unit** — Sellerboard counted exactly one MCF unit (MBUKB1, ASIN B0CX1WMVQV) in January
   and excludes MCF in the other five months. Our exclusion is correct: `SalesChannel = "Non-Amazon"`,
   Amazon posts no financial event. Affects Jan cog (−86.71), commission (−30.07), FBA (−30.27).

## Step 4 — Verify

- `reconcile --marketplace UK` now exits **0**, with its 4 cog cells reported as `KNOWN_TARGET_DEFECT`,
  not `WITHIN_DRIFT` and not `INVESTIGATE`.
- US/CA/AU exit codes and reports unchanged (US's exit 1 is pre-existing: locked targets 9/15).
- **Movement test:** perturb a registered defect's magnitude beyond its tolerance → it must fire
  `INVESTIGATE`. Revert. This proves the status pins rather than excuses.
- Existing perturbation tests (`cog × 1.20`) still fire on all marketplaces.

## Guardrails

- No band widened. `KNOWN_TARGET_DEFECT` tolerance is tight around the measured Δ.
- Register the **measured** UK Δ (+$1,000.62), not the unverified 28%/2% magnitudes.
- No reconciliation math, no attribution, no mapping changes. No new files beyond what Step 2 needs.
- Do not mark anything verified without evidence; the UK magnitude stays open with Elena.

## Definition of done

- `config.py` UK cog currency = GBP; `cog_needs_fx()` correct for all four; no reported number moves.
- `KNOWN_TARGET_DEFECT` status added; exit code gates on `INVESTIGATE` only; defects reported loudly.
- Three defects registered with evidence notes and tight tolerances around measured magnitudes.
- UK exits 0; movement test fires `INVESTIGATE`; other marketplaces unchanged.
- No band widened, no workbook edited, no math touched.
# Claude Code Task — Isolate the −$1.46 Sponsored Products residual before Step 2

## Context

The Step 1 Ads probe (`reference/data/ads_probe.md`, raw
`ads_probe_2026-02_raw.csv`) reconciled Feb 2026 ad spend against Sellerise to 0.006% on the
total. Three of four active lines matched to the cent; **only Sponsored Products was off, by
−$1.46.** The write-up labels this "almost certainly the V2 boundary-day effect."

That label was written **before the test that would confirm it.** This task runs that test.
Do not build Step 2 or edit any pull logic yet — this is a diagnosis over data we already
have.

Why the label is suspect: a month-boundary attribution edge would land on whichever products
had spend near Feb 28 / Mar 1, not surgically on Sponsored Products while Sponsored Brands and
Sponsored Display are exact to the cent. Competing explanations that fit the evidence equally:
daily-rounding accumulation (SP has the most rows, so per-day rounding sums largest there), or
a handful of SP campaigns the report treats differently. The point is to name the cause, not
assume it.

## Operating rules

- Diagnosis only — no changes to the pull, mapping, or persistence. Read `ads_probe_2026-02_raw.csv`
  (and re-pull one report only if a needed field is missing).
- Report actual numbers per test. State the verdict as what the data shows, not the expected answer.
- Change nothing to "fix" it — a sub-dollar residual is acceptable; this task decides how to
  **label** it, not whether to chase it.

## Test A — Boundary-day split (is it the V2 edge?)

The probe pulled `date.value` daily, so this needs no new data.

- Sum Sponsored Products `totalCost` (USD only) for **Feb 1–27** and compare to Sellerise's
  Feb SP figure; then isolate **Feb 28** alone.
- If nearly all of the −$1.46 sits on the boundary day(s) (Feb 28, and/or a Mar-1 attribution
  edge), the V2 boundary hypothesis is **confirmed**.
- If the −$1.46 is smeared across many days, it is **not** a boundary effect → go to Test B.

## Test B — Daily-rounding accumulation (is it summing rounding?)

- For Sponsored Products, count the daily rows and sum the absolute day-level deltas vs a
  higher-precision recomputation (or vs Sellerise daily if available).
- Compare SP's row count to SB's and SD's. If SP's residual scales with its row count while
  SB/SD (far fewer rows) land at 0.00, that's consistent with per-day rounding accumulating,
  not a boundary edge.
- Check the sign: rounding tends to be small and **consistently same-signed** relative to the
  rounding rule; a boundary effect need not be.

## Test C — Per-campaign outlier (is it a few campaigns?)

- The probe required `campaign.id` in the query. Group SP `totalCost` by `campaign.id` and look
  for a small number of campaigns carrying the bulk of the −$1.46 (e.g. a campaign in an unusual
  delivery/cost-type state, or one straddling the currency filter).
- If 1–3 campaigns own the residual, that's the cause — record their IDs and what's distinct
  about them.

## Cross-month shape check (adjudicator)

Using the Jan and Mar–Jun reports (re-pull minimally if not cached), tabulate the SP residual
per month with its **sign and magnitude**, and note where that month's SP spend clustered
(early vs late). Then read the shape:

- Residual roughly tracks which side of the month spend fell on, sign varies → **boundary (V2)**.
- Residual consistently same-signed and scaling with SP row count each month → **rounding**.
- Residual traces to the same campaign(s) each month → **per-campaign**.

"It's small again" is **not** a verdict — small-and-consistent is exactly what rounding looks
like. The shape, not the size, names the cause.

## Definition of done

- A short verdict appended to `reference/data/ads_probe.md`: which of boundary / rounding /
  per-campaign the −$1.46 actually is, backed by the Test A–C numbers and the cross-month shape.
- The write-up's "almost certainly the V2 boundary-day effect" line **corrected** to the
  evidenced cause (or downgraded to "sub-dollar SP residual, cause: <finding>").
- An explicit accepted-residual note: whatever the cause, a sub-dollar SP delta on a ~$23k month
  is within tolerance and will not be chased — but it is now correctly labeled.
- No pull/mapping/persistence code changed. Step 2 remains unblocked and starts only after this
  verdict is written.
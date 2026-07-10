# Claude Code Task — Diagnose the flat −$1,340/month net residual (verify before fixing)

## Context

After wiring `adExpenses` into net, the ~$18k/month gap closed to a residual of roughly
−$1,340/month (cumulative −$8,042 Jan–Jun, −3.84% of Sellerise net). The write-up labels this
"P&L-side purchase-date attribution drift." **That label doesn't fit the shape of the data,
and this task tests it before anything is fixed.**

Why the label is suspect — the shape is diagnostic:
- Purchase-date attribution drift moves revenue *between adjacent months*, so it **flips sign
  month-to-month and nets toward zero** cumulatively (as the Principal deltas did:
  −7,108 / +8,142 / +2,675 / …). It does not accumulate.
- This residual is **negative every single month** and **roughly uniform**
  (−1,367 / −1,155 / −1,481 / −856 / −1,543 / −1,640). Same-signed + flat + accumulating is
  the signature of a **systematic per-month over-subtraction**, not inter-month timing.

So something subtracted from net is consistently ~$1,340/month too large. This is a diagnosis,
not a fix: **name the bucket first.**

## Operating rules

- **Verify before reconciling or fixing.** Do not change net math, mappings, or attribution
  until the residual is traced to a specific bucket with numbers.
- Diagnosis runs over data already in the report / DB. Re-pull only if a needed field is missing.
- Report actual per-bucket numbers; state the verdict as what the data shows.

## Test 1 — March per-bucket decomposition (the key discriminator)

March is the clean probe: its **ad total reconciled to 0.00**, so ads is removed as a variable,
yet March net is still −$1,481. Whatever is off in March is isolated to a non-ad bucket and is
almost certainly the same thing off in every month.

- For March, compute ours − Sellerise for **each** net-contributing bucket:
  `chargesObject` (by sub-line: Principal, Tax, ShippingCharge, …), `feesObject`, `fbaObject`,
  `refundsObject`, `storageFee`, `cog`, `adExpenses`. Include `salesTaxes` (derived).
- Assert the per-bucket deltas **sum to the −$1,481 net delta** (sanity check the decomposition
  is complete — if they don't sum, the net formula has an unaccounted term, which is itself the
  finding).
- The bucket(s) carrying the −$1,481 is the answer. Rank buckets by absolute contribution.

## Test 2 — Confirm it's systematic (same bucket every month)

- Repeat the per-bucket decomposition for all six months (Jan–Jun).
- For the bucket Test 1 fingered, check it carries a similar ~$1,340 same-signed delta every
  month. If yes → confirmed systematic, single cause. If the offending bucket *changes*
  month-to-month → it's not one systematic line and the "flat residual" read is wrong; report that.

## Test 3 — Route by what Test 1/2 name (do NOT pre-fix)

Branch on the fingered bucket:

- **`adExpenses`** (despite the ad *total* matching Sellerise's monthly figure): the ad total
  matching does **not** prove same-month attribution. Test whether Amazon attributes ad *cost*
  by a date that slots differently into Sellerise's P&L month than ours does — bucket ad spend
  by candidate dates and see if one closes the flat residual while keeping the monthly totals
  intact. This is the V2 date-basis question, now tested against **net** rather than line parity.
- **A double-subtraction / sign error at the net wiring** (a flat offset is exactly this
  shape): check whether the SP-API `ProductAdsPayment.AdvertisingFee` audit line (~$20k/mo) is
  being subtracted *in addition to* the Ads-API total, and whether any fee/tax/refund line
  changed sign or got double-counted when ads were wired in. Diff the net formula's terms
  pre- and post-ads-wiring.
- **A revenue/fee/cog line** with a fixed per-month basis mismatch: identify the sub-line and
  the mismatch (e.g. a fee Sellerise nets that we don't, a cog rate applied to a different unit
  basis). Report it; don't fix yet.

## Guardrails

- A flat same-signed accumulating residual is **not** "attribution drift" — do not relabel it as
  such without Test 1/2 evidence. Attribution drift nets toward zero; this doesn't.
- Don't widen tolerance to make −3.84% "pass." $1,340/month flows straight into net, the number
  the dashboard exists to report.
- Change one variable at a time; if Test 3 points at a date-basis fix, prove it closes net
  before committing it.
- Leave the ads-line reconciliation (PASS_DRIFT) and the settled revenue lines untouched — this
  is about what's *subtracted* into net, not the lines that already reconcile.

## Definition of done

- A written diagnosis at `reference/data/net_residual_diagnosis.md` with the March per-bucket
  decomposition (Test 1), the six-month confirmation (Test 2), and a named cause — the specific
  bucket/sub-line carrying the ~$1,340/month, backed by numbers.
- The report's "purchase-date attribution drift" label **corrected** to the evidenced cause.
- If the cause is a bug (double-subtraction/sign) → flagged for a one-line fix in a *separate*
  follow-up, not applied inside this diagnosis.
- If the cause is a real basis difference (date/unit) → the fix tested to confirm it closes net
  across settled months before committing; otherwise documented as a named, quantified accepted
  residual (not "drift").
- No net math, mapping, or attribution changed inside this task.
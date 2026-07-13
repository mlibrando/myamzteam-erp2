# Claude Code Task — Diagnose UK's −13.4% net residual (it was never actually diagnosed)

> **SUPERSEDED PREMISES (two).** Body left as written. See
> [`../data/decisions_audit.md`](../data/decisions_audit.md).
>
> - **Step 2's analogy to CA is built on a refuted reading.** "CA's bug was cog derived from US by a
>   fixed multiplier (×1.35) instead of real costs" — no. The CA sheet is **CAD**; ×1.350 is a
>   correct CAD markup. CA's cog was fixed by joining the US sheet so that a **USD cog meets
>   Sellerise-CA's USD `cog`**, a currency fix, not a cost-quality fix. The CA precedent therefore
>   says nothing about UK per-SKU cost quality.
> - **The UK cog gap is a Sellerise-side defect, not ours.** The component cost build-up validates
>   the UK sheet (ABDB 78.53, GMAKER-3 30.94, MBUKB1 96.06 all tie out to invoice). Sellerise
>   understates ABDB and MBUKB1; it matches GMAKER-3. Do **not** run the "is UK cog wrong / derived"
>   line of inquiry, do **not** edit the UK workbook, and do **not** retune our cog toward
>   Sellerise's implied values.
>
> UK's other driver — the `fbaObject` −$458 same-signed residual, labelled "Amazon post-snapshot
> restatement" — remains the project's one **untested** label. It rests on a rate-signature
> inference; no re-pull experiment has been run.

## Context

Final rollout table shows: US +1.70%, CA −3.50% (after its cog fix), **UK −13.39%** of net
cumulatively. UK reads 0 INVESTIGATE on both guards, and the rollout doc treats UK as "reconciles
cleanly" — but that assessment predates the May/Jun ads persistence and the CA cog investigation.

**Two claims in the current results contradict each other:** "CA now reconciles better than UK"
and "UK done, 0 INVESTIGATE." If CA at −3.5% required a full diagnosis-and-fix, UK at −13.4%
(8× US, ~4× CA) cannot be finished. UK is now the worst-reconciling marketplace and it never got
the per-bucket decomposition CA got. That −13% was in the table the whole time; attention was on CA.

There is also a monitoring problem: **0 INVESTIGATE while net is −13% off** means UK's bands are
absorbing a residual larger than the guards can see — the same "band hiding an unfixed problem"
failure just corrected on CA, but silent here because no single cell breaches while net is badly off.

## Operating rules

- **Diagnose before fixing.** Decompose UK per bucket; name the mechanism; then decide fix vs accept.
- Verify with numbers over data in hand. State the verdict from the SKU-vs-month / bucket evidence.
- Do not touch US, CA, or AU. Do not widen tolerance.

## Step 1 — Per-bucket decomposition of UK net Δ (all six months, ads-complete)

- Confirm UK May/Jun ads are persisted (they were completed) so every month is ads-clean.
- Decompose UK net Δ per bucket per month (`chargesObject` by sub-line, `feesObject`, `fbaObject`,
  `refundsObject`, `storageFee`, `cog`, `adExpenses`, derived `salesTaxes`). Assert per-bucket
  contributions sum to measured net Δ (sanity ≈ 0).
- Rank buckets by contribution. Note the **sign**: UK is net-negative (we under-count vs Sellerise)
  — the opposite of US (+). Different sign can mean different mechanism; don't assume it mirrors CA.

## Step 2 — Prime suspect: UK COGS source (run the CA diagnosis on UK)

CA's bug was cog derived from US by a fixed multiplier (×1.35) instead of real costs. Step 1 of the
CA work also found CA *prices* are US×1.144 — i.e. the workbook uses made-up per-marketplace
multipliers. **UK may have the identical latent bug.**

- Inspect the UK COGS workbook sheet: is UK per-SKU cog **independently entered**, or is it
  `US_cog × N` for some N? Report the exact derivation and the ratio per SKU.
- If UK cog is a derived multiple, run the same LOO-CV / flat-null test CA got: does substituting a
  corrected UK cost source (US-parity or true UK costs) collapse UK's cog residual and flip it from
  same-signed to mixed-sign? UK is the "control" the CA writeup claimed uses ≈US-parity cog — verify
  that claim is actually true, because a −13% net residual is not consistent with UK cog being right.

## Step 3 — If the driver isn't cog, name what it is

UK has fee/tax structure US/CA don't (`DigitalServicesFee`, VAT family, `ShippingTaxDiscount`
passthrough). A −13% same-signed residual could be a mis-mapped UK-specific line:

- Check whether any UK-specific leaf added in the rollout is mis-routed — e.g. a fee that should
  reduce net landing in `expenses` (excluded), or a VAT/passthrough leaf accidentally included in
  net, or `DigitalServicesFee` netted with the wrong sign. Re-verify each rollout-added UK rule
  against its Sellerise sub-line target across all six months (not just the UK Jan spot-check that
  was done at build time).
- The build only verified UK Jan `DigitalServicesFee = −$52.02`. Verify the full UK-specific
  mapping set month-by-month; a rule right in Jan can be wrong in a month with different composition.

## Step 4 — Decide, and fix the monitoring too

- If a systematic mechanism is found (cog basis or mis-mapped leaf): fix it, re-run, confirm UK's
  net Δ drops toward the low mixed-sign band US/CA sit in.
- **Regardless of fix:** UK's drift bands are mis-tuned — they read 0 INVESTIGATE at −13% net.
  After any fix, re-derive UK bands from corrected observed drift so the guard would actually catch
  a residual this size. A guard that says "all clear" on a 13%-off marketplace must not survive this
  task. Verify with the perturbation acceptance test.
- If (unlikely) the −13% is genuinely irreducible structure, it must be named per-bucket with
  evidence and the bands flagged as compensating for a known gap — not left as silent 0 INVESTIGATE.

## Guardrails

- −13% same-signed is a systematic-bug fingerprint, not drift — do not accept it without the Step 1
  decomposition and the Step 2 cog-source check.
- Verify the "UK uses ≈US-parity cog" claim from the CA writeup; a −13% residual suggests it may be
  false.
- Do not widen bands to keep UK at 0 INVESTIGATE; the goal is to close the residual, then tune bands
  to catch its size.
- Do not touch US/CA/AU numbers.

## Definition of done

- UK per-bucket decomposition (6 months) with the driving bucket(s) named and signed.
- UK COGS source derivation reported; if derived-multiplier, corrected and re-run (CA-style),
  showing the residual collapse and sign flip.
- All rollout-added UK mappings re-verified month-by-month against Sellerise sub-line targets.
- UK net Δ brought to the low mixed-sign band (or the residual named per-bucket with evidence).
- UK drift bands re-tuned so a −13%-scale residual would fire INVESTIGATE; perturbation test passes.
- No US/CA/AU change; no tolerance widened.
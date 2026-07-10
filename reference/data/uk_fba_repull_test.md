# S2 / S2′ — the UK FBA residual: named, and closed

Run 2026-07-10 in two passes. The re-pull and both hypothesis tests were **read-only** — no row was
written to `sp_transactions`, `sp_breakdowns`, `sp_transaction_items`, `pnl_monthly`,
`pnl_monthly_snapshots` or `sync_state`, and the re-pull went to a scratch file. No band was widened.

> ## Verdict
>
> **The −£458.45 is Sellerise omitting GMAKER-3's FBA fulfilment fee.**
>
> Amazon charged **£479.15** for GMAKER-3 over **142 units** Jan–Jun (£3.374/unit). Sellerise carries
> **£27.75** for the same SKU and the same 142 units (£0.195/unit) — a **94.2 % understatement**.
> In **five of six months the entire `fbaObject` bucket gap equals that SKU's Amazon-charged fee to
> the penny.**
>
> Two rival explanations are **refuted**, not merely displaced:
> - **Amazon post-snapshot restatement** — 867 re-pulled transactions came back byte-identical and
>   the FBA figure moved by £0.00; `chargesObject.Principal` matches Sellerise to the cent in all six
>   months (§ 1).
> - **Netting of refunded units' fees** — there are *zero* Refund-side FBA leaves in the UK feed, and
>   reconstructing the fees anyway closes ≤ 58 % (§ 2).
>
> **`KNOWN_TARGET_DEFECT`.** The five settled `fbaObject` cells are pinned in
> `drift_bands.TARGET_DEFECTS` at their measured Δ, tolerance ±£15. `reconcile --marketplace UK` now
> exits **0** with 0 INVESTIGATE and 9 `KNOWN_TARGET_DEFECT`. **Do not "fix" our FBA figure — it is
> the fee Amazon actually billed.**

All amounts are **GBP**. (The prior docs write this residual as `$458`; UK's sheet and Sellerise-UK's
`cog` are GBP — see `decisions_audit.md` S7.)

The sequence matters and is worth keeping: the label was refuted *before* the cause was found, and
the cells were held at `INVESTIGATE` in between. Had they been pinned to the restatement label to get
UK green, the guard would now be certifying a claim the evidence kills.

---

## Step 0 — the "before" snapshot exists

`sp_transactions` upserts on `transaction_id` and bumps `ingested_at = now()` on conflict
(`finances.py:268-276`), so the ingest timestamps say whether the originals survive. They do:

| fact | value |
|---|---|
| UK rows in `sp_transactions` | 2,011 |
| distinct `ingested_at` values | 6 — one per posted month |
| ingest window | `2026-07-07 07:38:19` → `07:38:28` UTC, a single pass |
| rows re-ingested since | **none** |

The stored UK rows are the original bytes from the 2026-07-07 pull. Step 1 could run today.

**Interval available to the test: 3 days** (2026-07-07 → 2026-07-10). That is a real interval, not
the 36 seconds the earlier "evidence" rested on — but it is days, not the weeks over which
restatement is supposed to accumulate. Section 1b is what carries the refutation; the re-pull alone
would be underpowered and is reported as such.

---

## Step 1 — Amazon vs Amazon

Re-pulled two settled UK months via `FinancesV20240619.list_transactions` into scratch, and diffed
against the stored originals.

### 1a. The re-pull

| | Feb 2026 | Mar 2026 |
|---|---:|---:|
| stored transactions | 432 | 435 |
| fresh transactions | 432 | 435 |
| present in both | 432 | 435 |
| vanished / newly appeared | 0 / 0 | 0 / 0 |
| **byte-identical raw JSON** | **432 / 432** | **435 / 435** |
| FBA leaves, stored | −1,334.19 | −1,409.26 |
| FBA leaves, fresh | −1,334.19 | −1,409.26 |
| pipeline subset feeding `fbaObject` (stored) | −673.87 over 189 leaves | −657.68 over 182 leaves |
| pipeline subset feeding `fbaObject` (fresh) | −673.87 over 189 leaves | −657.68 over 182 leaves |
| transactions whose FBA total moved | **0** | **0** |
| **Δ (fresh − stored)** | **+0.00** | **+0.00** |

867 transactions, whole raw payload, **not one cent moved**. To close Feb the FBA figure would have
had to be ~£117 (bucket) / ~£135 (per-unit line) smaller when Sellerise saw it — a 17–19 % revision.

### 1b. The argument that does not depend on the interval

If Amazon had restated this data between Sellerise's snapshot and our 2026-07-07 pull, the
restatement would have to have touched the FBA line **and nothing else**. It didn't touch anything
else, because nothing else disagrees:

| month | `chargesObject.Principal` Δ | `Commission` + `ReferralFee` Δ | `fbaObject` bucket Δ |
|---|---:|---:|---:|
| 2026-01 | **0.0000** | −118.05 | −71.35 |
| 2026-02 | **0.0000** | 0.00 | −117.25 |
| 2026-03 | **0.0000** | 0.00 | −87.10 |
| 2026-04 | **0.0000** | 0.00 | −60.35 |
| 2026-05 | **0.0000** | 0.00 | −61.20 |
| 2026-06 | **0.0000** | 0.00 | −61.20 |
| **Σ** | **0.0000** | **−118.05** | **−458.45** |

Revenue agrees with Sellerise's frozen snapshot **to the cent, in every month**. The referral fee
agrees to the cent in five of six (Jan's −118.05 is the documented `Commission ↔ ReferralFee` split).
Those numbers come from the *same transactions* that carry the FBA fee.

Amazon restating a fee line by 10–24 % while leaving the principal on those same transactions
identical to the penny is not a credible mechanism. Combined with 1a, that settles it.

> **Step 1 verdict: RESTATEMENT REFUTED.** The label `"Amazon post-snapshot restatement drift"` is
> wrong. Do not pin these cells on it.

*(Calibration, for the record: Sellerboard restates only its trailing settled month, by ≈$0.10.
Amazon's own restatement of settled UK months, measured here over 3 days: exactly £0.00.)*

---

## Step 2 — the netting hypothesis

**Hypothesis:** Sellerise computes its FBA line net of FBA fees on returned units, the way it
computes `cog` as `(units_sold − units_refunded) × unit_cog`.

### 2a. There are no FBA-fee refund leaves to net

Every FBA leaf in UK Jan–Jun, by transaction type:

| leaf | on `Shipment` | on `Refund` |
|---|---:|---:|
| `FBAPerUnitFulfillmentFee` | 1,749 leaves | **0** |
| `FBAFees` | 3 leaves (Jun, DEFERRED) | **0** |
| any FBA reversal / credit leaf | — | **0** |

Amazon does not refund the FBA fulfilment fee when a unit is returned, and it emits no reversal leaf.
Sellerise's `refundsObject` likewise has **no FBA line** — its keys are identical to ours
(`Commission`, `DigitalServicesFee`, `Principal`, `Promotion`, `RefundCommission`, `ShippingCharge`,
`ShippingChargeback`, `ShippingTax`, `Tax`, `Tax Withheld`). And no other Sellerise bucket carries an
FBA line. So the brief's literal form of the hypothesis — *"identify FBA fee refund / reimbursement
components"* — has **no candidate leaves at all.**

### 2b. So test the implied form: deduct the fee those units were actually charged

For each refunded unit, find the fee Amazon charged on its own shipment line, matched on
`(order_id, sku)` at the item level. 69 of 78 refunded units matched (the other 9 were shipped before
our window).

| refund attributed to | Σ\|Δ\| before | Σ\|Δ\| after | closed |
|---|---:|---:|---:|
| refund's **posted** month | 458.45 | **194.12** | 58 % |
| refund's **purchase** month | 458.45 | **225.68** | 51 % |

Per month, on the better (posted) attribution:

| month | gap to close | FBA fee of refunded units | residual | refunded units |
|---|---:|---:|---:|---:|
| 2026-01 | −71.35 | −47.89 | −23.46 | 10 |
| 2026-02 | −117.25 | −61.33 | −55.92 | 14 |
| 2026-03 | −87.10 | −110.81 | +23.71 | 24 |
| 2026-04 | −60.35 | −36.82 | −23.53 | 8 |
| 2026-05 | −61.20 | −26.58 | −34.62 | 7 |
| 2026-06 | −61.20 | −28.42 | −32.78 | 6 |
| **Σ** | **−458.45** | | **−146.60** | |

It removes roughly half and leaves a **same-signed** residual in five of six months. On the purchase
attribution it over-corrects January and under-corrects everything else. **Netting is not the
explanation.** It may be one component; it is not the mechanism, and no arrangement of it closes the
gap.

### 2c. Two other candidates, eliminated

- **Replacements / MCF-style shipments** (FBA fee charged, no revenue): **zero** such items. Every
  UK item carrying an FBA fee also carries a non-zero `OurPricePrincipal`.
- **Misclassification into `expenses`**: Sellerise's reimbursement and inbound lines reconcile to our
  leaves exactly. Jan: `MISSING_FROM_INBOUND + REVERSAL_REIMBURSEMENT + WAREHOUSE_DAMAGE +
  COMPENSATED_CLAWBACK` = 1,304.82 = our `FBAInventoryReimbursement + FBAReversedReimbursement`.
  `Inbound Transportation Fee` −346.14 = our `FBAInboundTransportationFee +
  FBAInboundTransportationProgramFee`. Δ = 0.00 for Jan–Apr. The FBA gap is not hiding in `expenses`.

---

## What Step 1 and Step 2 left standing

The shipment set is identical — `Principal` matches to the cent. On those same units:

| month | units | Amazon charged £/unit | Sellerise implied £/unit | gap |
|---|---:|---:|---:|---:|
| 2026-01 | 208 | 3.584 | 3.241 | 9.6 % |
| 2026-02 | 201 | 3.547 | 2.963 | 16.4 % |
| 2026-03 | 178 | 3.530 | 3.041 | 13.9 % |
| 2026-04 | 117 | 3.859 | 3.343 | 13.4 % |
| 2026-05 | 72 | 3.608 | 2.758 | 23.6 % |
| 2026-06 | 81 | 3.855 | 3.100 | 19.6 % |

Sellerise's `fbaObject` is not a sum of Amazon's charged FBA fees — it sits 9.6–23.6 % below them on
an identical shipment set. Oddly, *our* blended rate was the **more** stable of the two (coefficient
of variation 4.2 % vs 6.7 %), which a fixed per-SKU fee table applied to the same units cannot
produce. At that point the residual was **`UNEXPLAINED`**, and the five cells stayed `INVESTIGATE`.

---

# S2′ — the cause, from one SKU

Sellerise's own per-unit FBA fee for **GMAKER-3**, read out of Sellerise: **£27.75 across 142 units,
Jan–Jun.** Our unit count for the same SKU and window, on the same purchase-date basis the report
uses: **142**. Exact match, so the two sides are describing the same units.

## 1. The shortfall

| | Amazon (charged, from `sp_transactions`) | Sellerise | shortfall |
|---|---:|---:|---:|
| total FBA, GMAKER-3, Jan–Jun | **−£479.15** | −£27.75 | **£451.40** |
| units | 142 | 142 | — |
| **£/unit** | **3.374** | **0.195** | **94.2 % understated** |

Per month, straight off the `FBAPerUnitFulfillmentFee` leaves:

| month | GMAKER-3 units | Amazon charged | £/unit |
|---|---:|---:|---:|
| 2026-01 | 21 | −71.35 | 3.398 |
| 2026-02 | 35 | −117.25 | 3.350 |
| 2026-03 | 26 | −87.10 | 3.350 |
| 2026-04 | 24 | −81.05 | 3.377 |
| 2026-05 | 18 | −61.20 | 3.400 |
| 2026-06 | 18 | −61.20 | 3.400 |
| **Σ** | **142** | **−479.15** | **3.374** |

£451.40 against a £458.45 gap: **98.5 %** of the whole `fbaObject` residual, from one SKU.

## 2. It is not an aggregate coincidence — it reconciles month by month, to the penny

The sharper result. Compare each month's **entire** `fbaObject` bucket gap against GMAKER-3's
Amazon-charged fee alone:

| month | `fbaObject` bucket gap | GMAKER-3's Amazon fee | difference |
|---|---:|---:|---:|
| 2026-01 | −71.35 | −71.35 | **0.00** |
| 2026-02 | −117.25 | −117.25 | **0.00** |
| 2026-03 | −87.10 | −87.10 | **0.00** |
| 2026-04 | −60.35 | −81.05 | +20.70 |
| 2026-05 | −61.20 | −61.20 | **0.00** |
| 2026-06 | −61.20 | −61.20 | **0.00** |
| **Σ** | **−458.45** | **−479.15** | **+20.70** |

**In five of six months the entire UK FBA residual *is* GMAKER-3's fulfilment fee, exact to the
penny.** Sellerise books **nothing** for it. April is the single exception: there it booked exactly
£20.70, and that £20.70 is the *whole* of the six-month difference.

Read the other way — what Sellerise implicitly booked for GMAKER-3, if every other SKU is priced at
Amazon's charged fee — the answer is £0.00 in five months and £20.70 in April, Σ £20.70. Against the
£27.75 Sellerise actually reports, that leaves **£7.05** across six months and thirteen other SKUs:
**0.27 %** of the ~£2,600 non-GMAKER-3 FBA base. Rounding.

## 3. This also explains the one loose end from Step 2

Sellerise's implied per-unit rate looked *less* stable than ours (CV 6.7 % vs 4.2 %) — the fact that
argued against a fixed rate table. It is now obvious why: Sellerise's figure is our figure with **one
SKU zeroed out**, and GMAKER-3's share of monthly units swings from 10 % to 25 %.

| month | GMAKER-3 units / total | observed gap % |
|---|---:|---:|
| 2026-01 | 21 / 208 = 10.1 % | 9.6 % |
| 2026-02 | 35 / 201 = 17.4 % | 16.4 % |
| 2026-03 | 26 / 178 = 14.6 % | 13.9 % |
| 2026-04 | 24 / 117 = 20.5 % | 13.4 % ← the month Sellerise booked £20.70 |
| 2026-05 | 18 / 72 = 25.0 % | 23.6 % |
| 2026-06 | 18 / 81 = 22.2 % | 19.6 % |

The gap tracks GMAKER-3's unit share, scaled by its slightly-below-average fee. April is low for
exactly the reason above. Nothing is left over.

## 4. Every pinned Δ decomposes into two named components

The guard cells are on `fbaObject.FBAPerUnitFulfillmentFee`, not on the bucket. The difference is
Sellerise's `FBAFees` line — its deferred-shipment *estimate*, which we no longer have a counterpart
for because those shipments have all released. Both pieces are named:

| month | GMAKER-3's fee, omitted | Sellerise's `FBAFees` estimate | sum | cell Δ in the report |
|---|---:|---:|---:|---:|
| 2026-01 | −71.35 | −8.71 | −80.06 | **−80.06** |
| 2026-02 | −117.25 | −17.84 | −135.09 | **−135.09** |
| 2026-03 | −87.10 | −8.93 | −96.03 | **−96.03** |
| 2026-04 | −60.35 | 0.00 | −60.35 | **−60.35** |
| 2026-05 | −61.20 | −3.10 | −64.30 | **−64.30** |
| 2026-06 | −61.20 | 0.00 | −61.20 | −61.20 *(trailing)* |

No unexplained remainder anywhere.

---

## Resolution — pinned

Registered in `drift_bands.TARGET_DEFECTS`, five settled cells, tolerance **±£15** — reused from
`_UK_PRIOR_PULL_BANDS[("fbaObject","FBAPerUnitFulfillmentFee")]`, the calibrated pull-to-pull
movement for that cell, not a fraction of the defect:

| marketplace | month | cell | expected Δ | tolerance |
|---|---|---|---:|---:|
| UK | 2026-01 | `fbaObject.FBAPerUnitFulfillmentFee` | −80.06 | ±15.00 |
| UK | 2026-02 | `fbaObject.FBAPerUnitFulfillmentFee` | −135.09 | ±15.00 |
| UK | 2026-03 | `fbaObject.FBAPerUnitFulfillmentFee` | −96.03 | ±15.00 |
| UK | 2026-04 | `fbaObject.FBAPerUnitFulfillmentFee` | −60.35 | ±15.00 |
| UK | 2026-05 | `fbaObject.FBAPerUnitFulfillmentFee` | −64.30 | ±15.00 |

`2026-06` carries the same defect (−61.20) but is the trailing month and still moving; its band
handles it. A trailing month is never pinned.

**Result:** UK goes from 5 INVESTIGATE + 4 `KNOWN_TARGET_DEFECT` to **0 INVESTIGATE + 9
`KNOWN_TARGET_DEFECT`**, and `reconcile --marketplace UK` exits **0** for the first time. `WITHIN_DRIFT`
(149) and `TRAILING` (30) counts are unchanged — nothing was reclassified into a band, and **no band was
widened**. US, CA and AU reports are byte-identical.

### The pin holds; it does not excuse

| check | result |
|---|---|
| Δ at the measured value | `KNOWN_TARGET_DEFECT` |
| Δ ±£14 (inside tolerance) | `KNOWN_TARGET_DEFECT` |
| Δ ±£16 (moved) | `INVESTIGATE`, both directions |
| **Δ → 0.00, i.e. Sellerise fixes the SKU** | **`INVESTIGATE`** (unpinned it would read `WITHIN_DRIFT`) |
| an unregistered cell at the same Δ, band 50 | `INVESTIGATE` — the pin widens nothing |
| `fbaObject × 1.20` perturbation, all 5 cells | `INVESTIGATE` on both guards |
| one extra GMAKER-3 unit's fee (£3.37) | still `KNOWN_TARGET_DEFECT` — tracks the defect, not noise |
| five extra units (£16.87) | `INVESTIGATE` |
| `cog × 1.20` regression test | still fires on US / CA / UK |

The vs-prior-pull guard is deliberately **not** told about the registry: it compares our-now against
our-then, where a target defect contributes nothing, and suppressing cells there would blind the one
guard that can still catch a code regression in them.

### Two live consequences

1. **The Δ scales with GMAKER-3's monthly volume.** A new settled month needs its own entry. This is
   not a rate defect that can be pinned once.
2. **If Sellerise corrects the SKU's fee, these cells will fire `INVESTIGATE`** — by design, because
   their Δ will have moved to zero. That is the signal to delete the entries, and the only clean way
   this ends.

### What must not be done

Our FBA figure is the fee Amazon actually billed, taken straight from the `FBAPerUnitFulfillmentFee`
leaves. **Do not adjust it toward Sellerise's**, do not widen the band, and do not touch the
`fbaObject` mapping. The defect is on the target's side. The fix is Sellerise's to make.

---

## Method / reproducibility

- Re-pull: `FinancesV20240619.list_transactions`, `postedAfter=2026-02-01T00:00:00Z`,
  `postedBefore=2026-03-01T00:00:00Z` (and the March window), single page each, written to a scratch
  JSON file. `sync_state` was never read or written; `_process_page` was never called.
- FBA leaves extracted with the pipeline's own `finances.breakdown_leaves_for_txn`, so the "before"
  and "after" sides are flattened identically.
- Our monthly figures come from `reconcile.compute_pnl_in_memory(shipment_basis="purchase",
  refund_basis="posted")` — exactly what `reconcile_report_UK.md` reports.
- Per-item FBA fees and per-SKU rates read directly from `sp_transactions.raw_json`, reproducing the
  report's `fbaObject` column to the cent as a sanity check.
- Post-run check: UK `ingested_at` still has 6 distinct values, all `2026-07-07`; `sync_state`
  untouched; `pnl_monthly_snapshots` UK batch count unchanged.

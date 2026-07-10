# Cross-marketplace decisions audit — v2

Re-run 2026-07-10 against corrected sources. **Every cell reports what the code does**, not what a
doc claims. Where code and doc still disagree, the disagreement is the finding and both are cited.

This run supersedes the v1 audit of the same name. V1 was correct in method and surfaced the three
real blockers, but it defended two doc conclusions that evidence outside the corpus has since
overturned: it argued the UK cog gap was our workbook's fault, and it inherited the "CA sheet is a
fake ×1.35 markup" framing. Both are corrected below. See § 5 for exactly what changed and why.

> **UPDATE 2026-07-10 (later the same day).** Three of this audit's own findings have since been
> closed, and the table below reflects the post-fix state:
>
> - **S7 / D3.6 — resolved.** The UK sheet is **GBP**, its native currency. `config.py:74` now says
>   so, and `cog_needs_fx("UK")` is `False`. No reported number moved (verified: all four reports
>   byte-identical across the change).
> - **S6 / D2.7 — resolved.** `KNOWN_TARGET_DEFECT` is now a real status in `drift_bands.py`, backed
>   by a registry that **pins** a diagnosed target-side Δ to its measured magnitude instead of
>   widening its band. UK's 4 `cog` cells and AU's 4 Jan cells are registered. UK's INVESTIGATE count
>   fell 9 → 5. **UK still exits 1.** See § 7.
> - **S2 / D3.2 — tested; the label is REFUTED and the residual is now NAMED.** The UK `fbaObject`
>   residual is not Amazon restatement (867 re-pulled transactions byte-identical, `Principal` exact
>   to the cent) and not refund-netting (no Refund-side FBA leaves exist). **It is Sellerise omitting
>   GMAKER-3's FBA fulfilment fee** — Amazon charged £479.15 over 142 units; Sellerise carries £27.75.
>   In five of six months the whole bucket gap equals that SKU's fee to the penny. The five settled
>   cells are now pinned as `KNOWN_TARGET_DEFECT`, and **`reconcile --marketplace UK` exits 0** for
>   the first time. See [`uk_fba_repull_test.md`](uk_fba_repull_test.md) and § 8.

Legend:

- **`UNVERIFIED`** — the value is wired and running, but nothing tests it. Not a bug; an absence of
  evidence.
- **`KNOWN_TARGET_DEFECT`** — our side is right and the reconciliation *target* is wrong. The
  residual is real, named, and must not be "fixed" on our side. Now a machine-checked status, not
  just prose: `drift_bands.TARGET_DEFECTS` pins each such Δ, and the cell fires `INVESTIGATE` the
  moment it moves — including toward zero, because the target fixed its bug.

Pointers are `file:line`, resolved against the working tree as of this update; every one was
verified to point at the content it claims. Code lives under `backend/sync/`; findings under
`reference/data/`; prompt/spec history under `reference/prompts/`.

Everything marked *(measured)* was re-derived for this audit against the live database or the
workbook. § 6 lists every check that was run.

---

## 1. Decisions table

| Decision | US (`ATVPDKIKX0DER`) | CA (`A2EUQ1WTGCTBG2`) | UK (`A1F83G8C2ARO7P`) | AU (`A39IBJ37TRP1C6`) |
|---|---|---|---|---|
| **Reconciliation target** | Sellerise · `SELLERISE_RAW_DATA.json` (`reconcile.py:61`) | Sellerise · `SELLERISE_RAW_DATA_CA.json` (`:62`) | Sellerise · `SELLERISE_RAW_DATA_UK.json` (`:63`) | Sellerboard · `SELLERBOARD_RAW_DATA.json` (`sellerboard.py:60`). `reconcile.py:65` sets `None`; `:106` raises for AU |
| **Reconciler module** | `sync/reconcile.py` | `sync/reconcile.py` | `sync/reconcile.py` | `sync/reconcile_au.py` (separate engine) |
| **Revenue attribution (Shipment)** | purchase-date, postedDate fallback (`attribution.py:70-83`). Σ\|Δ\| 39,569.53 → 9,748.02 (`reconcile_report_US.md:21`) | purchase-date. 3,505.26 → 1,708.10 (`reconcile_report_CA.md:21`) | purchase-date. 9,221.07 → 1,776.83 (`reconcile_report_UK.md:20`) | purchase-date (`reconcile_au.py:99`). Settled on **unit counts**: purchase matches SB `units` 5/6 months, posted 0/6 (`reconcile_au.py:85-90`) |
| **Refund dollars basis** | posted — **re-derived at runtime**, not read from config (`reconcile.py:551`; tie → posted). posted $1,699.51 vs purchase $10,332.00 (`reconcile_report_US.md:17`) | posted, runtime-derived. $61.28 vs $1,866.58 (`reconcile_report_CA.md:17`) | posted, runtime-derived. $407.08 vs $3,210.63 (`reconcile_report_UK.md:16`) — **measured, not inherited** | posted, read from `config.MARKETPLACE_REFUND_BASIS` (`reconcile_au.py:78`). posted $20.31 vs purchase $1,829.02 (`config.py:141-143`) |
| ↳ *writer path* (`pnl_monthly`) | `aggregate.py` default `"posted"` (`:52,59`), never given the config value | ← same | ← same | AU never written to `pnl_monthly` (0 rows, *measured*) |
| **Refund COGS basis** | **purchase** (`config.py:125`). Scored on Σ\|net Δ\|: purchase $5,249.23 vs posted $5,970.98 (`net_residual_diagnosis.md:131-136`) | **posted** (`config.py:126`). Scored on Σ\|cog Δ\|: posted $2,596.90 vs purchase $3,090.23 — **`UNVERIFIED` post-override**, see D3.1 | **purchase** (`config.py:127`). Scored on Σ\|cog Δ\|: purchase $1,000.62 vs posted $2,135.40 (`rollout_ca_uk_results.md` Gate 2). Independently measured; matching US is coincidence | **posted** (`config.py:133`). Scored on refunded-unit **counts**: posted 6/6 exact, purchase Δ=−4 (`config.py:128-133`) |
| ↳ *wired in* | `cogs.py:143`, `reconcile.py:538` | ← same | ← same | `reconcile_au.py:79` |
| **COGS workbook sheet** | `US` (`config.py:80`) | `CA` (`:81`) | `UK` (`:82`) | `AU` (`:83`) |
| **Sheet's actual currency** | **USD** (`config.py:72`) | **CAD** — cost column is US × 1.350 (ratio 1.3493–1.3512), *measured*. Retail column is US × **1.1440** — a different multiplier, so the sheet was not FX-scaled wholesale *(measured)* | **GBP** (`config.py:74`) — its native currency, validated against the component cost build-up. The near-parity with US (30.94 vs 30.76) is a coincidence of magnitude; it was once read as evidence of denomination. **Corrected this run** (S7 / D3.6) | **USD cost column, AUD retail column** (`config.py:75`). Cost: AU/US ratio 1.0075 on GMAKER-3. Retail: AU/US 1.27–1.67 *(both measured)* |
| **COGS source override** | none | **CA → US** (`config.py:188-190`). Wired at `cogs.py:148`, `reconcile.py:263-264`, `reconcile_au.py:278` | none | none |
| **Effective cog currency** | USD | **USD** (override resolves to the US sheet, `config.py:87-93`) | **GBP** | USD |
| **`cog_needs_fx()` → converted?** | `False` → n/a | **`True` → NOT converted anywhere** (deliberate, D2.2) | **`False`** since S7 — cog and txns are both GBP, so the flag no longer misdescribes UK | `True` → **converted once**, `reconcile_au.py:289-314`; guard SKU `GMAKER-3` ∈ 40–50 AUD (`config.py:158-159`) |
| **Pipeline (txn) currency** | USD (`config.py:36`) | CAD (`:37`) | GBP (`:38`) | AUD (`:39`) |
| **Target currency** | USD throughout | revenue **CAD**, `cog` **USD** (`AU_SELLERBOARD_VERIFICATION.md:270`) | **GBP** throughout — Sellerise-UK's `cog` is GBP, matching our sheet | **USD** throughout (`sellerboard.py:8`) |
| **FX handling** | none | none | none | AU target adapter only. Reference rate from **refunds + ads anchors only** (`reconcile_au.py:369-388`); **absolute** band `FX_RATE_TOLERANCE = 0.02` (`sellerboard.py:389`), floor $5.00 (`:398`) |
| **Tax pass-through families** | `MarketplaceFacilitatorTax-{Principal,Shipping,Other}` (`bucket_map.py:82-84`) | `Shipment.Tax` (`:221-222`); `ShippingTaxDiscount` (`:92`) | `MarketplaceFacilitatorVAT-{Principal,Shipping}` (`:85-86`); `OurPriceTaxDiscount` (`:94`) | `Shipment.Tax` = 10 % GST (`:221-222`); `LowValueGoodsTax-{Principal,Shipping}` (`:87-88`). **`UNVERIFIED`** — D3.3 |
| ↳ *refund side* | MFT/VAT/LVGT-Principal → `refundsObject."Tax Withheld"` (`bucket_map.py:104-111`), resolved before passthrough (`:209-210`) | ← shared table | ← shared table | ← shared table |
| ↳ *rule scope* | The `Shipment`/`Refund` `.Tax` → passthrough rule (`bucket_map.py:221-222`) is **marketplace-agnostic**; it fires for any market emitting a bare `Tax` leaf, not just CA/AU | | | |
| **Marketplace-specific mappings** | — | `Shipment.Tax`, `ShippingTaxDiscount` → passthrough | `DigitalServicesFee` + `DigitalServicesFeeFBA` → `feesObject` (`bucket_map.py:133-134`); DSF reversal → `refundsObject` (`:176`); `EPRChargeback{EcoFee,ServiceFee}` → expected expenses (`aggregate.py:271-272`) | **MCF exclusion is not code.** No `S03`/`Non-Amazon` filter exists in `backend/`. MCF orders post no financial event, so `listTransactions` never returns them (`reconcile_au.py:103-113`) |
| **Ads — account** | single NA account, chosen by `"US" in countryCodes` (`ads_spend.py:314-315`) | ← same account | ← same account | ← same account |
| **Ads — SB Video** | `hsaCost + hsaVideoCost` merged into `Sponsored Brands` (`reconcile.py:624`; documented `:360`) | ← same rule | ← same rule | n/a (ads used only as an FX anchor) |
| **Ads — write filter** | keeps only `budgetCurrency.value == "USD"` (`ads_spend.py:140`) | ← **same filter drops all CAD rows** | ← **drops all GBP rows** | ← **drops all AUD rows** |
| **Ads — read filter** | `budget_currency = 'USD'` (`reconcile.py:336`) | `= 'CAD'` (`:336`) | `= 'GBP'` | `= 'AUD'` (`reconcile_au.py:195`) |
| ↳ *write ∩ read* | ✅ USD ∩ USD | ❌ **∅** — B2 | ❌ **∅** | ❌ **∅** |
| **Ads — observed Δ** | −$5.75 … +$3.06, one `FAIL` | **$0.00 all 6 months** | **$0.00 all 6 months** | anchor only, no band |
| **Drift bands — vs target** | `_US_SETTLED_BANDS` (`drift_bands.py:38-78`) | `_CA_SETTLED_BANDS` (`:87-117`) | `_UK_SETTLED_BANDS` (`:136-185`). Both its `cog` and `fbaObject` bands were sized to post-fix residuals that will never arrive; those 9 cells are now **pinned** in `TARGET_DEFECTS` instead. Neither band widened — D2.7 | **none** (`:192-197`, AU absent). `band_for()` silently falls back to **US dollar bands** (`:276`) — D2.4. AU's 4 Jan cells are pinned in `TARGET_DEFECTS`, read by `reconcile_au.py` directly |
| **Drift bands — vs prior pull** | `_US_PRIOR_PULL_BANDS` (`:319-354`) | `_CA_PRIOR_PULL_BANDS` (`:358-392`) | `_UK_PRIOR_PULL_BANDS` (`:396-431`) | **none** (`:436-440`) → US fallback |
| **Restatement profile sizing the bands** | Amazon/Sellerise: revenue-side ±$4,358.81 abs over 6 mo; ads $0.00 over ~13 h (`drift_baseline.md`); bands = 1.5–2× observed max | ← same profile, CA scale (~1/10 US) | ← same profile, UK scale (~1/6 US) | Sellerboard: **trailing settled month only, ≈$0.10** (`AU_SELLERBOARD_VERIFICATION.md:377-378,788`). Bands deliberately **unwired** pending a 5-clean-month derivation (`:784`) |
| **Known target-side defects** | none named; snapshot staleness is bidirectional | Sellerise restates month-boundary attribution Feb→Mar ±$199.50 / ±$9.98 | **`KNOWN_TARGET_DEFECT` — Sellerise understates the UK-exclusive bundle cog.** Registered: 4 `cog` cells, pinned at +242.84 / +177.87 / +184.41 / +122.62, tolerance ±25. Direction established by the component cost build-up (external); per-SKU magnitudes **`UNVERIFIED`**, see D3.5. **Second `KNOWN_TARGET_DEFECT`: Sellerise omits GMAKER-3's FBA fee** (£479.15 charged vs £27.75 carried, 142 units). Registered: 5 `fbaObject` cells, pinned at −80.06 / −135.09 / −96.03 / −60.35 / −64.30, tolerance ±15. Plus (unregistered, inside band): `Commission ↔ ReferralFee` split (net −£118, cancels except Jan); `chargesObject.Promotion` +£63 rounding; storage reclassified into `expenses.FBAFees` some months | **`KNOWN_TARGET_DEFECT` ×2, 4 cells** — Sellerboard **omitted GST from Jan storage** (−$52.75) (`AU_SELLERBOARD_VERIFICATION.md:638-658`); **counted 1 of 3 MCF units in Jan** (`:696,759`), moving Jan `cog` −86.71, `Commission` +30.07, `FBA` +30.27. All four registered |
| **Accepted net residual (Jan–Jun)** | **+$3,568.15 (+1.70 %)**, mixed-sign, per-cause labeled → ACCEPT (`reconcile_report_US.md:25`) | **−$374.48 (−3.50 %)**, mixed-sign, post cog-fix → ACCEPT (`reconcile_report_CA.md:25`) | **−$1,593.57 (−13.39 %)**, same-signed (`reconcile_report_UK.md:24`). **Not accepted, but re-attributed**: **both arms are now target-side defects, pinned**: the cog arm (~63 %, Sellerise understates per-SKU cost) and the FBA arm (~37 %, Sellerise omits GMAKER-3's fulfilment fee). Neither is our error. See D3.4 | **Σ −$232.57**, mixed-sign per month (`au_sellerboard_reconcile.md:115`). Jan closed at cause — both causes Sellerboard-side |
| **Locked validation targets** | 15 (`reconcile.py:73-89`) | **`[]`** (`:95`) | **`[]`** (`:96`) | **`[]`** (`:97`) |
| **INVESTIGATE, latest run** | 0 vs target / 0 vs prior pull | 0 / 0 | **0 vs target** **+ 9 `KNOWN_TARGET_DEFECT`** (4 `cog`, 5 `fbaObject`) / 0 vs prior pull. Was 9 INVESTIGATE before S6+S2′ | n/a (no bands) + **3 `KNOWN_TARGET_DEFECT`, 0 undiagnosed CONTENT flags** (`au_sellerboard_reconcile.md:87`) |
| **Exit code, latest run** | **1** — locked targets 9/15 PASS (pre-existing) | **0** | **0** — 0 INVESTIGATE. `KNOWN_TARGET_DEFECT` cells do not fail the run (`reconcile.py:1316`) | **0** — `reconcile_au.py` never gated on content flags |
| **cog residual, Jan–Jun** | Σ\|Δ\| $4,084.20, ΣΔ −$4,061.34, mixed-sign | Σ\|Δ\| $909.31, ΣΔ +$197.57, mixed-sign | Σ\|Δ\| $1,000.62, ΣΔ +$1,000.62, **6/6 same-signed** *(measured)* | gross-cog Σ −$86.71, all in Jan (`au_sellerboard_reconcile.md:135`) |

---

## 2. Discrepancies

### D1 — Code vs doc

**D1.1 — No file in the repository can produce the CA/UK/AU rows the reconciler reads.** ⚠ *highest severity*

`ads_spend.py:140` drops every CSV row whose `budgetCurrency.value != "USD"`, and it is the **only**
writer of `ad_spend_daily` (`:156` DELETE, `:164` INSERT — no other statement touches the table
anywhere in `backend/`). `:314-315` additionally pins the advertiser to the account with
`"US" in countryCodes`, regardless of `--marketplace`. But the readers select
`budget_currency = MARKETPLACE_CURRENCY[mp]` → `'CAD'` / `'GBP'` (`reconcile.py:336`) and `'AUD'`
(`reconcile_au.py:195`). Write set ∩ read set = ∅ for CA, UK and AU.

Those rows nevertheless exist. *(measured)* `ad_spend_daily` holds 5,190 CAD, 3,032 GBP and 3,010 AUD
rows. Three independent facts show `ads_spend.py` did not write them:

- **Row counts match the raw NA report exactly, per currency, per month.** `2026-01`:
  `{USD 5642, CAD 2213, AUD 1778, GBP 1704}` in `ads_probe_2026-01_raw.csv` — and the identical four
  numbers in the database. Same for Feb, Mar, Apr. The table is the single NA report split by
  `budgetCurrency.value` and tagged with the corresponding `marketplace_id`.
- **`as_of` collides to the microsecond across marketplaces.** CA, UK and AU share one `as_of` in
  *all six* months; May and June share it with US too (e.g. `2026-05 → 08:29:14.293871` on all four).
  `_replace_month` stamps `dt.datetime.now()` once per `(marketplace, month)` (`ads_spend.py:264`),
  and `sweep_ad_spend` loops months for **one** marketplace — so separate runs cannot collide.
- `git log -p --follow -- backend/sync/ads_spend.py`: the USD filter is present in the file's only
  commit. It has never been absent.

`ads_multi_pull.py` is **not** the missing writer — it downloads the same NA report but persists it
to CSV on disk (`:105,116`) and never opens a database connection. *(checked)*

The intended design ("one NA account, split by `budget_currency`") is real. **The script that
implements it is not in the repository.** Running `python -m sync.ads_spend --marketplace CA` today
would `DELETE` the CA rows first (`:155-158`, by marketplace + date range, *before* the currency
filter is applied), then either insert USD rows tagged `CA` or — if the report returned no USD rows —
return having deleted and inserted nothing (`:159-161`). Either way `load_ad_spend("CA")` returns
`{}` afterwards and the reconciled CA/UK/AU ad spend is destroyed.

**D1.2 — `sellerboard.py`'s docstring forbids exactly what its loader does.**
`sellerboard.py:36-40`: *"Junk rows: do NOT filter on `has_data` or `status`. Both moved between the
2026-07-06 and 2026-07-09 pulls."* `load_sellerboard` then filters on both: `:168`
(`not period.get("has_data")`) and `_is_junk_row` at `:137` (`period.get("status") == "preparing"`).
Currently benign — in the present raw file every complete month has `has_data: true` and no `status`
key, so removing both filters yields the identical six months. It is a live trap for the next pull,
and it is the precise failure the docstring was written to prevent.

**D1.3 — `reconcile_au.py` tells the reader one term is borrowed from Sellerboard. Four are.**
The rendered text at `reconcile_au.py:574` reads *"Only the inventory-loss gap is borrowed from
Sellerboard."* The formula immediately below (`:581-592`) takes `refundsObject` (`:586`), `expenses`
(`:587`), `inventory_gap` (`:590`) **and** `adExpenses` (`:591`) from `theirs`.

Consequence: AU's Σ −$232.57 net residual is **not an independent check of refunds, expenses or ad
spend** — those three cancel identically on both sides by construction. The residual tests only
revenue, commission, FBA fee, storage and cog. This is stated nowhere.

**D1.4 — the refund-COGS basis was decided by three different metrics across four marketplaces.**
US on Σ\|**net** Δ\| (`net_residual_diagnosis.md:131-136`); CA and UK on Σ\|**cog-cell** Δ\|
(`rollout_ca_uk_results.md`, Gate 2); AU on refunded-unit **counts** (`config.py:128-133`).
`config.py:120-123` presents all of them as one homogeneous *"empirically tested per rollout task"*.
Only the AU basis was settled on a metric that cannot be confounded by dollar-side effects — a
discipline `reconcile_au.py:92-98` argues for at length, and which the other three predate.

**D1.5 — the Gate-2 US refund-dollars cell is a mislabelled copy of the COGS cell.**
`rollout_ca_uk_results.md`'s Gate-2 table gives the US row as
`posted (5,249) vs purchase (5,971) → posted | purchase (5,249) vs posted (5,971) → purchase`.
Both columns carry the *same two numbers* with the labels swapped. `5,249 / 5,971` are the
refund-**COGS** figures. The real US refund-**dollar** figures are posted $1,699.51 / purchase
$10,332.00 (`reconcile_report_US.md:17`). The *conclusion* (posted) is right; nothing in that cell
supports it. Headered in place.

*(Corollary, not a defect: UK's winning figure $1,000.62 is exactly its Σ\|cog Δ\| in the current
report. Not a copy artifact — it is the irreducible floor. Under the purchase basis the whole
remaining cog residual is the per-SKU value gap, which no attribution choice can move. The test
discriminated cleanly, $2,135.40 → $1,000.62.)*

---

### D2 — Load-bearing but undocumented (what breaks if "cleaned up")

**D2.1 — the CA override's refuted rationale survives in three more places.** *(config.py fixed this run)*

`config.py`'s `MARKETPLACE_COG_SOURCE_OVERRIDE` comment now states the true reason and the
consequence of removal. Three sites still record the old, refuted one and would have to be corrected
together:

- `cogs.py:155` — *"CA sheet is US×1.35, wrong basis"*
- `reconcile.py:260` — *"marketplaces whose workbook sheet has provisional cost values"*
- `drift_bands.py:83` and `:114` — *"a spurious FX-like multiplier"*, *"the now-fixed US×1.35
  cost-basis bug"*

The correct reading: the CA cost column is **CAD**, and 1.350 is the CAD/USD rate — a real
conversion. The retail column is US × **1.1440** *(measured)*, a different multiplier; a single
mechanical FX scaling would have moved both columns by the same factor. Sellerise-CA reports revenue
in CAD but `cog` in USD (`AU_SELLERBOARD_VERIFICATION.md:270`: cog ÷ our USD basis = 0.962, ÷ the
CA-sheet CAD basis = 0.745). The override exists to make the comparison **USD-vs-USD**.

**What breaks:** deleting the override once "real CA cost data lands" re-introduces a
**+$2,425.58 / +29.1 %** cog error across Jan–Jun *(measured, D4.1)* and reverts CA's net residual
from −$374.48 to ≈ −$2,774. Real CAD-sourced costs would make the override *more* necessary. The only
thing that retires it is Sellerise-CA reporting `cog` in CAD.

**D2.2 — `cog_needs_fx()` returns `True` for CA and UK, and nothing converts.**

`config.py:96-100` computes `cog_currency(mp) != MARKETPLACE_CURRENCY[mp]` — `True` for CA (USD cog vs
CAD txns) and UK (USD cog vs GBP txns). Its own docstring at `config.py:66-67` says such a
marketplace *"needs explicit FX handling at the point of use."* No such handling exists: the only
caller outside AU is `cogs.py:254`, which logs a warning and moves on. `_compute_net_ours`
(`reconcile.py:463-479`) subtracts a USD `cog` from CAD/GBP revenue.

This is **correct in effect and wrong in principle**: `_compute_net_theirs` (`:482-495`) makes the
identical category error on Sellerise's side, because Sellerise-CA reports a USD `cog` inside a CAD
P&L. The two errors are the same error and cancel.

**What breaks:** "fixing" `_compute_net_ours` to honour `cog_needs_fx` — converting CA's cog into CAD
before subtracting — introduces a ~35 % error into CA's net and breaks a reconciled marketplace,
because the target does not convert either. Today the flag means "this marketplace *would* need FX if
its target were native-currency" — which is true only for AU.

**D2.3 — AU's `MARKETPLACE_COG_CURRENCY = "USD"` is the load-bearing entry that looks like a typo.**

`config.py:75` labels the AU sheet USD while AU transactions are AUD. *(measured)* The AU sheet is
genuinely **mixed**: its cost column tracks US (GMAKER-3 30.99 vs US 30.76, ratio 1.0075) while its
retail column tracks AUD (AU/US retail 1.27–1.67, consistent with AUD/USD ≈ 0.67). Two different
multipliers in one sheet. It is guarded (`reconcile_au.py:296-299` raises if the flag flips) and
canary-tested (`GMAKER-3` must land in 40–50 AUD, `config.py:158-159`) precisely because both failure
modes produce believable numbers: ~21 AUD if multiplied instead of divided, ~63 AUD if divided twice.

**What breaks:** "correcting" AU's sheet currency to `AUD` — the obvious-looking cleanup, since the
sheet's retail column *is* AUD — makes `cog_needs_fx(AU)` return `False`, which trips the guard at
`reconcile_au.py:296` and hard-fails AU. That is the good outcome. The bad outcome is someone
removing the guard first.

**D2.4 — `band_for()` falls back to US dollar bands for any unknown marketplace, and AU is unknown.**

`drift_bands.py:276`: `DRIFT_BANDS_BY_MARKETPLACE.get(marketplace_id or "", _US_SETTLED_BANDS)`.
Same at `:476` for prior-pull bands and `:224` for ad bands. AU is deliberately absent (`:192-197`).
`reconcile_au.py` never calls `band_for`, so today this is inert.

**What breaks:** the moment anyone routes AU through `reconcile.py`'s guard — the natural move when
wiring the live pipeline — AU gets US bands ($1,500 on `chargesObject.Principal`) applied to **AUD**
amounts at ~1/20 of US scale, against a target whose real restatement is **≈$0.10**
(`AU_SELLERBOARD_VERIFICATION.md:788`). Every AU regression passes silently. The correct behaviour
for an unbanded marketplace is to refuse, not to inherit US.

**D2.5 — `MARKETPLACE_REFUND_BASIS` is read by exactly one caller, and it is not the one you'd think.**

`config.py:144-149` records refund-dollar bases for all four marketplaces. Its only consumer is
`reconcile_au.py:78` *(grep-verified)*. For US/CA/UK the value is **decorative**:

- `reconcile.py:551` re-derives the winner at runtime by minimising Σ\|Δ\| on `refundsObject`
  (`refund_winner = "posted" if posted_delta <= purchase_delta else "purchase"`).
- `aggregate.py` — the module that actually writes `pnl_monthly` — defaults to `"posted"` (`:52,59`),
  and `__main__.py:90` calls `aggregate_marketplace(conn, marketplace_id)` without the argument, so
  the default always wins.

Today all three agree on `posted`, so nothing is visibly wrong. **What breaks:** editing
`MARKETPLACE_REFUND_BASIS` for US/CA/UK is a silent no-op. Conversely, if a future month's data made
`purchase` win the runtime test, `reconcile.py` would flip basis mid-flight while `aggregate.py` kept
writing `posted`, and `pnl_monthly` would diverge from the report that "validates" it, with no signal.

**D2.6 — `reconcile.py` never reads `pnl_monthly`.** `load_pnl` (`:130-146`) is defined and **never
called** *(grep-verified: one hit, the definition)*. Every number in the reports comes from
`compute_pnl_in_memory` (`:149`) and `compute_cog_by_basis` (`:238`). This is what keeps the reports
correct while the table is stale (D4.1), and it means **a green reconcile report says nothing about
the contents of `pnl_monthly`** — the table the dashboard is specified to read (`PLAN.md`).

**D2.7 — the UK reclassification voids the design intent of two UK drift bands.** *(new this run;
**cog arm RESOLVED** — § 7. The `fbaObject` arm was then **tested** — § 8.)*

As found, `_UK_SETTLED_BANDS` sized `cog.(scalar)` to `$100` and
`fbaObject.FBAPerUnitFulfillmentFee` to `$50` against residuals it expected to disappear — the
comments read *"SIZED TO POST-WORKBOOK-FIX"* and *"SIZED TO POST-RESTATEMENT-FIX"*, with *"Once the
workbook is corrected, INVESTIGATE goes quiet."* (`drift_bands.py:156-158,179-183`; the fbaObject
comment has since been corrected — see § 8.)

Under the corrected classification **the workbook will never be corrected** — it is right, and
Sellerise is wrong. So the 4 `cog` INVESTIGATE cells fire permanently. The 5 `fbaObject` cells fire
until S2 is run. Because `reconcile.py:1316` gates the exit code on `inv_s == 0`,
`python -m sync.reconcile --marketplace UK` **returns 1 forever**, with no remediation path that is
permitted.

**Resolution (S6):** the 4 `cog` cells are now pinned in `drift_bands.TARGET_DEFECTS` (`:553`) and
read `KNOWN_TARGET_DEFECT`, which does not fail the run. Neither band was widened. The 5 `fbaObject`
cells were **not** registered — at that point their "restatement" label was an untested inference,
and pinning them would have asserted as diagnosed what had never been measured. **UK therefore still
exits 1.**

**And the restraint paid.** S2 subsequently refuted the restatement label outright (§ 8). The
`fbaObject` band is now the honest signal for an `UNEXPLAINED` residual rather than a countdown to a
fix that was never coming. Its comment no longer claims restatement; the band was not widened.

This is a design gap, not a bug: the guard has no way to express "this Δ is a known *target* defect,
hold it at its measured magnitude and alarm only if it moves." US, CA and AU record their target
defects in prose; UK now needs one in code. Out of scope to change here — recorded as S6.

---

### D3 — `UNVERIFIED` cells (wired, never tested)

**D3.1 — CA's refund-COGS basis was scored on pre-override cog values and never re-run.**

Gate 2 chose `posted` for CA on `posted $2,596.90 vs purchase $3,090.23`. That `$2,596.90` is
**exactly** the pre-override CA cog Σ\|Δ\| — the override's own comment records its effect as
*"Σ\|Δ\| 2597 → 909"*, and the current report gives Σ\|Δ\| = **$909.31**. So the basis test was scored
against a cog cell computed from the CA sheet (CAD, US × 1.35), which the override then changed by
~29 % per month *(measured, D4.1)*. **The purchase arm was never recomputed post-override.** The
winner plausibly still holds — the override rescales both arms roughly monotonically — but it is
asserted, not measured. Re-running the A/B under the override is a ~10-minute job. → **S1**

**D3.2 — UK's FBA −£458 label was the project's last untested claim. It has now been tested, and it
was wrong.** *(**RESOLVED as refuted** — see § 8)*

- Refund **dollars**: measured, and re-measured on *every* reconcile run (`reconcile.py:551`):
  `posted £407.08 vs purchase £3,210.63`. Not inherited.
- Refund **COGS**: measured independently — `purchase £1,000.62 vs posted £2,135.40`. It coincides
  with US; it was not copied from US. CA's `posted` in the same table proves the test discriminates
  per marketplace.
- **FBA residual −£458.45, same-signed 6/6 months**: was labelled *"Amazon post-snapshot restatement
  drift"*, resting **entirely on a rate-signature inference**, with no re-pull test ever run. The
  only pull-to-pull evidence was the vs-prior-pull guard over a **36-second** window, which cannot
  observe a weeks-scale restatement.

**Tested 2026-07-10** ([`uk_fba_repull_test.md`](uk_fba_repull_test.md)):

- Re-pulled UK Feb and Mar 2026 from SP-API into scratch. **867 / 867 transactions byte-identical**;
  the FBA figure moved by **£0.00**. Zero transactions gained, lost or changed.
- Independently of that 3-day window: `chargesObject.Principal` matches Sellerise's frozen snapshot
  to **0.0000 in all six months**, and `Commission + ReferralFee` in five of six. A restatement that
  moved the FBA line 9.6–23.6 % while leaving the principal on those *same transactions* identical to
  the penny is not a credible mechanism. **The label is refuted.**
- The netting hypothesis was tested too: there are **no Refund-side FBA leaves anywhere** in the UK
  feed, and Sellerise's `refundsObject` has no FBA line either. Reconstructing the fee Amazon actually
  charged on each refunded unit (matched on `order_id` + `sku`) and deducting it closes at most 58 %
  of the gap and leaves a same-signed residual of ≈ −£147. **Not the explanation.**
- What was left after S2: Sellerise's `fbaObject` is not a sum of Amazon's charged FBA fees. Same
  shipment set, a per-unit rate 9.6–23.6 % lower, and *less* stable month to month than ours
  (CV 6.7 % vs 4.2 %). At that point the residual was **`UNEXPLAINED`** and the five cells stayed
  `INVESTIGATE`.

**Then S2′ named it (same day).** Sellerise's own per-unit fee for **GMAKER-3** is £27.75 across 142
units Jan–Jun (£0.195/unit). Amazon charged **£479.15** over the same 142 units (£3.374/unit) — a
**94.2 % understatement**, £451.40 of a £458.45 gap. And it is not an aggregate coincidence: **in five
of six months the entire `fbaObject` bucket gap equals GMAKER-3's Amazon-charged fee to the penny**
(April alone differs, by exactly £20.70, the one month Sellerise booked anything). Each pinned cell Δ
decomposes exactly into `(GMAKER-3's omitted fee) + (Sellerise's FBAFees deferred-estimate line)`.
This also explains the CV anomaly above: Sellerise's figure is ours with one SKU zeroed, and
GMAKER-3's unit share swings 10 %→25 % month to month.

**Status: `KNOWN_TARGET_DEFECT`.** The five settled `fbaObject` cells are pinned at their measured Δ,
tolerance ±£15. **UK exits 0.** Our FBA figure is the fee Amazon billed — do not adjust it. → § 8

**D3.3 — AU's GST pass-through is inferred from CA/UK and is unverifiable against Sellerboard.**
`bucket_map.py:218-222` routes `Shipment.Tax` to passthrough for AU with the comment *"Sellerise
treats these as net-zero on the AU/CA reconciliation"* — but AU has no Sellerise target. The routing
was inherited: `AU_SELLERBOARD_VERIFICATION.md:124` — *"the rule was inherited from CA/UK, where that
leaf is a facilitator tax on sales."* Sellerboard exposes no GST line — `vatTotal`, `vatFacilitator`,
`vatCosts` are all zero on all periods, and are listed as unmapped at `sellerboard.py:110-115`.
`AU_SELLERBOARD_VERIFICATION.md:239`: *"Record AU sales-GST as inferred, not verified. A clean net
does not prove it."* What *was* measured is the **10 % GST magnitude on Amazon fees** (9.99–10.01 %
on two independent leaves, every month, `sellerboard.py:62-67`) — a different claim.

**D3.4 — UK's net residual is now split across two causes with different owners, and neither is closed.**
Σ −$1,593.57. The cog arm (+$1,000.62 on the cog cell, ~63 % of the deficit) is a
`KNOWN_TARGET_DEFECT` as of this audit — real, ours-is-right, and **not** to be fixed on our side.
The FBA arm (−$458, ~37 %) is D3.2's untested label. "Not accepted" therefore no longer means "we may
have a bug": it means one arm awaits a policy decision (D2.7 / S6) and the other awaits an experiment
(S2).

**D3.5 — the UK per-SKU understatement magnitudes cannot be verified from this repo, and as stated
they do not reconcile with the measured aggregate.** *(new this run)*

The corrected direction — Sellerise understates, our workbook is right — is established externally by
the component cost build-up and does **not** depend on any magnitude. The magnitudes do not survive
contact with the data:

- Sellerise's API exposes **only monthly aggregate `cog`**, never a per-SKU breakdown
  (`unit_cog_comparison.md`, § Method "Limitation"). **No per-SKU Sellerise unit cost is observable
  from anything in this repository.** The `implied cog` column in that doc is proportional
  attribution, which by construction assigns every SKU the same −5.06 % gap — an output of its own
  assumption, not a measurement. It is not evidence for or against 28 % / 2 %.
- *(measured)* Reproducing `cogs.py`'s exact attribution per SKU gives Jan–Jun UK net units
  ABDB 113, GMAKER-3 127, MBUKB1 23, and total pipeline cog **$18,367.67** — matching the
  reconcile-accurate figure to the cent, so the method is sound. Against Sellerise's $17,367.05 the
  measured Δ is **+$1,000.62**.
- A 28 % ABDB understatement implies `113 × (78.53 − 56.54) = +$2,484.69` from ABDB alone (or
  +$1,941.16 under the reading `S = wb / 1.28`), plus ~$44 from MBUKB1 at 2 %, and $0 from GMAKER-3.
  To land on +$1,000.62 the remaining eleven SKUs would have to contribute **−$1,528** (or −$984).
  Their *entire* pipeline cog is $3,355.02, and one of them (`B5-FUC0-5AKB`, 71 units, missing from
  the UK sheet) can supply at most ≈ −$448. The rest would have to sit ~30–46 % **below** Sellerise —
  the opposite direction from every UK/US ratio in the corpus (1.006×–1.590×, median 1.030×).
- If ABDB alone carried the whole Δ, its understatement would be **11.3 %**, not 28 %.

Caveat that cuts both ways: the aggregate Δ conflates unit-count differences with unit-cost
differences, and Sellerise's per-SKU **unit counts** are as unobservable as its unit costs. So the
28 % figure is not *refuted* here — it is **`UNVERIFIED`, and inconsistent with the aggregate under
the natural equal-count assumption by a factor of ~2.5**. Recorded, not propagated. The reclassification
stands on the build-up alone.

**D3.6 — the UK sheet's cog currency was asserted, not established.** *(new this run; **RESOLVED**)*

`config.py:74` used to declare `MARKETPLACE_COG_CURRENCY[UK] = "USD"` with the reason *"UK sheet holds
US-parity values"* — resting on GMAKER-3 at 30.94 vs US 30.76. The corrected ground truth writes the
same workbook numbers as **£**78.53 / **£**30.94 / **£**96.06. Both could not be right, and the flag
was load-bearing: it was what made `cog_needs_fx(UK)` return `True` (D2.2).

*(measured)* The margin-coherence test pointed at GBP but was not decisive on its own. Taking
GMAKER-3, whose UK retail is 130.95: if the UK cost column is GBP, the margin is 76.4 %, closely
matching CA's 77.3 % (CAD/CAD) and AU's 77.3 % (after converting its USD cost to AUD). If the cost
column is USD, the margin is 82.6 %, above US's own 80.8 %.

**Resolved (S7): the UK sheet is GBP**, its native currency — settled from the component build-up's
own denomination, which is the only source that can answer the question. `config.py:74` now reads
`"GBP"`, and `cog_needs_fx("UK")` is `False`. Nothing downstream moved: our UK cog and Sellerise's
UK `cog` were always in the same denomination, so the comparison was self-consistent either way, and
all four reconcile reports are byte-identical across the change *(verified)*. What the fix buys is
that `cog_needs_fx` now means what its docstring says for every marketplace but CA — and CA's `True`
is deliberate (D2.2), not an accident.

**D3.7 — CA, UK and AU have no locked validation targets.** `reconcile.py:95-97` — all three are `[]`.
US carries 15 (`:73-89`). `main()` requires `locked_pass == len(result["locked"])` (`:1316`), so for
CA/UK/AU that clause is `0 == 0` — vacuously true. Their exit codes are governed by the drift guards
alone.

**D3.8 — AU drift bands are unwired by design.** `drift_bands.py:192-197`. The intended derivation —
five clean months, excluding January's two Sellerboard artifacts — is specified but not done
(`AU_SELLERBOARD_VERIFICATION.md:784-788`). See D2.4 for what the fallback does meanwhile.

---

### D4 — Stale data

**D4.1 — `pnl_monthly` CA `cog` holds the pre-override value, and is mislabelled `USD`.** *(measured)*

| month | stored `pnl_monthly` | CA-sheet join (no override) | override value (what the code computes today) | Δ stored − override |
|---|---:|---:|---:|---:|
| 2025-12 | 148.91 | 148.91 | 122.66 | +26.25 |
| 2026-01 | 1,925.07 | 1,925.07 | 1,445.51 | +479.56 |
| 2026-02 | 2,225.85 | 2,225.85 | 1,676.52 | +549.33 |
| 2026-03 | 2,054.66 | 2,054.66 | 1,622.51 | +432.15 |
| 2026-04 | 911.80 | 911.80 | 643.95 | +267.85 |
| 2026-05 | 1,318.83 | 1,318.83 | 1,222.02 | +96.81 |
| 2026-06 | 2,164.64 | 2,164.64 | 1,591.01 | +573.63 |
| **Σ** | **10,749.76** | **10,749.76** | **8,324.18** | **+2,425.58 (+29.1 %)** |

The stored figures reproduce the CA-sheet join **to the cent, every month** (Σ difference 0.0000).
Rows were written `2026-07-07 07:46:59`, before the override existed. The US control passes: the same
recompute reproduces the stored US rows to the cent for all 8 months (Σ\|Δ\| = 0.0000), so the
recompute is faithful and only CA is stale.

Second defect on the same rows: *(measured)* all 7 CA `cog` rows carry `currency = 'USD'` while
holding a CAD-scale value. Every other CA bucket is correctly labelled `CAD` (28 `chargesObject`,
41 `refundsObject`, …). This is *not* `cog_currency()` resolving the override —
`git log -p -- backend/sync/cogs.py` shows the original code wrote a hardcoded `"USD"` literal,
replaced by `row_currency` (`cogs.py:253`) only in `03afafb`.

**Blast radius:** none for `reconcile.py` (D2.6 — it computes cog in memory). Everything for any
consumer that reads `pnl_monthly` directly, which `PLAN.md` specifies the dashboard will do. A re-run
of `sync.cogs --marketplace CA` fixes both the amount and the label — but see B1, because the module
that must run first currently crashes.

**D4.2 — AU has zero rows in `pnl_monthly`.** *(measured)* US 280 rows, UK 247, CA 169, AU **0** —
all buckets, including `cog`. `cogs_per_sku` has 13 AU SKUs, but nothing reached `pnl_monthly`;
`reconcile_au.py` reads `sp_*` directly and never touches it. `PLAN.md`'s rollout acceptance check
(*"`pnl_monthly` has non-empty rows for each of CA / UK / AU"*) is unmet.

**D4.3 — the stale cog has already propagated into `pnl_monthly_snapshots`.** Snapshot `pull_at`
values are two days *newer* than the CA cog rows they nominally correspond to. Narrower than it looks:
`reconcile.py:931-937` snapshots the **in-memory** `diffs`, so the snapshot's `cog` cell is the
override value, not the table's. The two disagree; nothing reconciles them.

**D4.4 — the evidence base is still not under version control.** The 22 spec/prompt docs are now at
`reference/prompts/` (moved this run, from an accidental `reference/data/reference/prompts/`), and
the whole directory is **untracked**; the original root paths show as unstaged deletions.
`git clean -fd` deletes them. Several rows above cite them as the sole evidence for a wired value
(`AU_SELLERBOARD_VERIFICATION.md`, `AU_CLOSE_JANUARY.md`, `REFUND_COG_FIX.md`,
`RESOLVE_CA_COG_RESIDUAL.md`). **`git add -A` would fix this in one command; it has not been done,
because staging was outside this audit's remit.**

---

## 3. What must be resolved before the live pipeline

### Blocks the live pipeline / dashboard

**B1 — `python -m sync` crashes on every marketplace.** `__main__.py:94` reads `agg_stats["groups"]`.
`aggregate_marketplace` returns no `"groups"` key (`aggregate.py:61-70` returns `transactions`,
`leaves`, `mapped`, `unmapped_pairs`, `skipped_zero`, `pnl_rows`, `fallback_txns`,
`fallback_by_month`). The `KeyError` fires **after** Phase 2 has committed its `pnl_monthly` writes
and **before** Phase 3 runs COGS at all. The documented full-pipeline entrypoint has therefore never
completed for any marketplace, and it fails in the worst possible place: `pnl_monthly` rewritten,
`cog` rows left untouched from the previous run. **This is also why D4.1 exists.**

**B2 — the ads loader for CA/UK/AU does not exist in the repo, and running the one that does is
destructive.** (D1.1) Reproducing today's CA/UK/AU ad spend from a clean checkout is impossible.
`sync.ads_spend --marketplace CA` deletes the reconciled CAD rows first (`ads_spend.py:155-158`),
then inserts USD rows the reader will never select. Either commit the loader that produced the
current rows, or teach `ads_spend.py` to route rows to marketplaces by `budgetCurrency.value` instead
of filtering to USD. Until then `ad_spend_daily` is unreproducible state, and CA/UK/AU net residuals
depend on it.

**B3 — `pnl_monthly` CA `cog` is stale by +$2,425.58 (+29.1 %) and mislabelled `USD`.** (D4.1)
Harmless to `reconcile.py`, fatal to the dashboard, which `PLAN.md` specifies reads `pnl_monthly`
only. Fixed by re-running `sync.cogs --marketplace CA` — which requires B1 first if run via
`python -m sync`, though `python -m sync.cogs --marketplace CA` reaches it directly.

**B4 — AU has no `pnl_monthly` rows at all.** (D4.2) `PLAN.md`'s acceptance check is unmet. AU's
reconciliation lives entirely in `reconcile_au.py`, which bypasses the table.

**B5 — `band_for()` silently hands AU the US dollar bands.** (D2.4) Inert today, live the moment AU is
routed through the shared guard. An unbanded marketplace should raise, not inherit. A one-line
behavioural question, explicitly out of scope for this audit to change.

### Should be tested, but does not block

**S1 — re-run CA's refund-COGS A/B under the override.** (D3.1) The chosen basis was scored on cog
values the override then changed by 29 %. Cheap to settle; currently an assertion.

**S2 — the UK FBA −£458 label.** (D3.2) ✅ **RUN — label REFUTED.** § 8.

**S2′ — name the UK FBA residual.** ✅ **DONE — Sellerise omits GMAKER-3's FBA fee.** Five cells
pinned; UK exits 0. § 8.

**S2″ — the two live consequences of that pin.** *(new)*
- The pinned Δ **scales with GMAKER-3's monthly unit volume**, so each new settled month needs its own
  registry entry. This is not a rate defect that can be pinned once and forgotten.
- If Sellerise corrects the SKU's fee, the five cells will fire `INVESTIGATE` — by design, since their
  Δ moves to zero. That is the signal to delete the entries, and the only clean way this ends.
  Raise the fee with Sellerise; it is a defect on their side, not ours.

**S3 — decide what `MARKETPLACE_REFUND_BASIS` is for.** (D2.5) Authoritative for AU, decorative for
US/CA/UK. Either wire `aggregate.py` and `reconcile.py` to read it, or delete the three unread
entries. Leaving it as-is guarantees someone eventually edits a value and observes nothing.

**S4 — reconcile `sellerboard.py`'s docstring with its loader.** (D1.2) The filters are benign against
the current file and were written to be impossible. One of the two is wrong.

**S5 — correct the three remaining sites that record the CA override's refuted rationale.** (D2.1)
`cogs.py:155`, `reconcile.py:260`, `drift_bands.py:83,114`. `config.py` was corrected this run.

**S6 — give the drift guard a way to express `KNOWN_TARGET_DEFECT`.** (D2.7) ✅ **DONE** — § 7.

**S7 — settle the UK sheet's cog currency from the component build-up.** (D3.6) ✅ **DONE** — § 7.

### Documented and accepted — no action

- **US +$3,568.15 (+1.70 %)** — mixed-sign, every month labelled per cause;
  `net_residual_diagnosis.md` records ACCEPT.
- **CA −$374.48 (−3.50 %)** — mixed-sign, post cog-fix; Σ\|cog Δ\| $909.31, no INVESTIGATE.
- **AU Feb–Jun** — mixed-sign, within FX bands; **January closed at cause**, and both causes are
  Sellerboard-side: it omitted GST from one storage line (−$52.75), and counted 1 of 3
  Multi-Channel-Fulfilment units. Our pipeline is correct on both. *(Caveat from D1.3: the AU net
  residual does not test refunds, expenses or ads — those are borrowed from the target.)*
- **AU MCF exclusion** — not a decision and not code. MCF orders (`S03-` prefix,
  `SalesChannel = Non-Amazon`) never generate a financial event, so `listTransactions` cannot return
  them. US/CA/UK exposure is $0.
- **UK Sellerise-side items** — `Commission ↔ ReferralFee` split (−$118, cancels except Jan),
  `chargesObject.Promotion` +$63 rounding, storage reclassified into `expenses.FBAFees` some months.
- **Sellerboard restatement profile** — trailing settled month only, ≈$0.10; Jan–May byte-identical
  across pulls. This is why AU bands must not be copied from the Amazon/Sellerise profile.

**UK's cog arm moves into this list in substance but not in status.** Σ −£1,593.57 (−13.39 %),
same-signed. ~63 % is now a `KNOWN_TARGET_DEFECT` on Sellerise's side, pinned in `TARGET_DEFECTS`,
and needs no pipeline fix. ~37 % is the FBA residual, whose restatement label S2 **refuted**; it is
now `UNEXPLAINED` and stays `INVESTIGATE`. UK is half diagnosed, half open — and the guard now says
exactly that: 4 pinned, 5 firing.

---

## 4. Corrections applied to the corpus this run

Superseded conclusions were **headered in place**, never deleted or rewritten.

| File | Superseded conclusion | Correct reading |
|---|---|---|
| `unit_cog_comparison.md` | UK "pipeline HIGH → update our workbook"; CA sheet "a pure US×1.35 artifact"; per-SKU `implied cog` presented as measurement | UK is a Sellerise-side defect; CA sheet is genuinely CAD; the implied-cog column is proportional attribution, not observation |
| `rollout_ca_uk_results.md` | "No pipeline fix… data-governance action (user updates UK sheet)"; "Provisional status… remove the override"; Gate-2 US refund-dollars cell | UK defect is target-side; override is permanent and currency-motivated; the US cell is a mislabelled copy (D1.5) |
| `RESOLVE_CA_COG_RESIDUAL.md` | "mechanically derived", "US×1.35 is the wrong CA cost" | CA cost column is CAD; 1.350 is the CAD/USD rate |
| `UK_RESIDUAL_DIAGNOSIS.md` | "CA's bug was cog derived from US by a fixed multiplier" (used to motivate suspecting UK cog) | CA's fix was a currency fix; the analogy does not transfer. UK sheet is correct |
| `SELLERBOARD_AU_VERIFY.md` | "Net uses `salesCosts`, not `productCosts`"; the `has_data`/`status` parser rule | `netProfit` uses `productCosts` (`sellerboard.py:29-34`, asserted); never filter on `has_data`/`status` |
| `AU_CURRENCY_RESOLVED.md` | "~$845 inventory-loss gap" | −$705.39 (`sellerboard.py:203-209`) |
| `PLAN.md` | (whole document) | Marked STALE; its two acceptance checks are unmet (B3, B4) |

**"Sellerboard entered raw AUD into a USD field" — nothing to mark.** An exhaustive search of
`reference/` finds this theory asserted or entertained in **zero** documents. Every AU currency doc
establishes the opposite directly (`AU_CURRENCY_RESOLVED.md:26` — *"confirmed in Sellerboard account
settings"*; `:31-32` — revenue/referral/FBA ratios ≈ 0.68 = real FX, cog ≈ 1.05 = same currency).
The theory appears only in the audit brief's own list of things to refute.

Generated reports (`reconcile_report_*.md`, `au_sellerboard_reconcile.md`) were **not** headered:
they are rewritten by `reconcile.py` / `reconcile_au.py` on every run, so a header would be lost.

The one permitted code change: `config.py`'s `MARKETPLACE_COG_SOURCE_OVERRIDE` comment now states the
true reason (USD-vs-USD comparison), that the entry must not be removed, the +$2,425.58 / +29.1 %
consequence of removing it, and the three sites still carrying the old rationale. **Verified
comment-only**: the parsed AST is byte-identical before and after, and `cog_source_marketplace`,
`cog_currency` and `cog_needs_fx` return the same values for all four marketplaces.

---

## 5. What v1 of this audit got wrong

V1's § 4 ("Two premises in the audit brief that the evidence does not support") argued that the UK
reclassification was mistaken. It was itself mistaken, and the error is instructive.

V1 wrote: *"The direction is inverted… The docs say our workbook overstates: `unit_cog_comparison.md`
— 'pipeline HIGH; workbook costs systematically above Sellerise'."* But **"our workbook is above
Sellerise" and "Sellerise is below our workbook" are the same sentence.** A two-sided comparison
measures a difference; it cannot say which side is right. V1 read the doc's *verdict column* as if it
were a *measurement*, and inherited the verdict.

What settles it is a third, independent source: the component cost build-up, which prices ABDB,
GMAKER-3 and MBUKB1 from invoice and ties out to the workbook exactly. That evidence sits outside the
corpus, so no amount of re-reading the corpus could have produced it — but the corpus also contains
nothing that *supports* the workbook-is-wrong verdict. It was an assumption from the start, made
plausible because the CA case had just been (mis)diagnosed the same way.

V1's second error follows from the first: it accepted "the CA sheet has a fake ×1.35 markup" while
simultaneously quoting `config.py`'s own contradiction of it, and filed the contradiction as a
documentation defect rather than resolving it. `AU_SELLERBOARD_VERIFICATION.md:276` had already
resolved it — *"The override works for the right numeric reason and the wrong stated reason."*

V1's three blockers (B1, B2, B3) were correct and are carried forward unchanged, with B2 now proven
from the database rather than inferred from report text.

---

## 6. Verification performed for this audit

Read-only throughout: code was read, not run; the database was queried with `SELECT` only; no
reconciliation was re-run and no decision re-derived. Nothing above is marked verified without a check
behind it.

| Check | Method | Result |
|---|---|---|
| Only writer of `ad_spend_daily` | grep every INSERT/DELETE in `backend/` | `ads_spend.py:156,164` — sole writer. `ads_multi_pull.py` writes CSV, never opens a DB connection |
| CA/UK/AU ad rows exist | `SELECT … GROUP BY marketplace_id, budget_currency` | CAD 5,190 · GBP 3,032 · AUD 3,010 · USD 34,431 |
| Those rows came from the NA report | per-currency row counts, DB vs `ads_probe_2026-0{1..4}_raw.csv` | exact match all four months (Jan: 5642/2213/1778/1704) |
| One writer pass wrote several marketplaces | `MAX(as_of)` per (month, marketplace) | CA+UK+AU share `as_of` to the microsecond in all 6 months; US joins them in May and Jun |
| `agg_stats["groups"]` KeyError | read `aggregate.py:61-70` vs `__main__.py:94` | no `"groups"` key returned |
| CA `pnl_monthly` cog stale | recompute `cogs.py`'s SQL under both cog sources | stored = CA-sheet join to the cent (Σ diff 0.0000); override Σ = 8,324.18; stale by +2,425.58 (+29.1 %) |
| US control on the same recompute | same SQL, US | reproduces stored US rows to the cent, all 8 months (Σ\|Δ\| 0.0000) |
| CA cog rows mislabelled | `SELECT bucket, currency` for CA | `cog` → `USD` (7 rows); every other CA bucket → `CAD` |
| AU `pnl_monthly` empty | `SELECT marketplace_id, count(*)` | AU absent entirely; US 280 · UK 247 · CA 169 |
| CA sheet is CAD, not FX-scaled wholesale | openpyxl, CA vs US per SKU | cost ratio 1.3493–1.3512 (n=11); **retail ratio 1.1440 for every SKU** |
| AU sheet is mixed-currency | openpyxl, AU vs US per SKU | cost ratio 1.0075 (GMAKER-3); retail ratio 1.27–1.67 |
| AU ground-truth figures "133.97 / 130.95 / 77 % margin" | search all four sheets | **not reproducible.** No sheet has retail 133.97; `130.95` is the **UK** sheet's GMAKER-3 price, not the US sheet's (US = 159.95). No AU SKU has a 77 % naive margin. The *conclusion* (AU cost column is USD) is confirmed by the two checks above and by `sellerboard.py:8` + the FX guard |
| UK workbook values | openpyxl, UK sheet | ABDB 78.53 · GMAKER-3 30.94 · MBUKB1 96.06 — tie out exactly |
| UK per-SKU units and cog | `cogs.py`'s exact SQL, grouped by SKU, purchase basis | ABDB 113 · GMAKER-3 127 · MBUKB1 23; total $18,367.67 = reconcile-accurate figure |
| UK 28 % / 2 % decomposition | arithmetic against the above | implies +$2,484.69 from ABDB alone; measured total is +$1,000.62. Requires the other 11 SKUs to sit 30–46 % below Sellerise. **Does not close** — see D3.5 |
| UK sheet currency | margin coherence vs CA/AU/US | GBP reading → 76.4 % margin (CA 77.3 %, AU 77.3 %); USD reading → 82.6 % (US 80.8 %). Suggestive, not decisive — D3.6 |
| `MARKETPLACE_REFUND_BASIS` consumers | grep `backend/` | one: `reconcile_au.py:78` |
| `load_pnl` callers | grep `backend/` | none — definition only |
| UK INVESTIGATE composition | UK report, before S6 | 4× `cog.(scalar)`, 5× `fbaObject.FBAPerUnitFulfillmentFee` |
| `config.py` Step-2 change is comment-only | `ast.dump()` before vs after; runtime re-check of the three resolver functions | AST identical; all four marketplaces resolve unchanged |

---

## 7. S6 + S7, implemented

Both were closed the same day, in that order. Nothing else in `backend/` changed.

### S7 — UK cog currency is GBP

`config.py:74`: `"A1F83G8C2ARO7P"` moves `"USD"` → `"GBP"`, and the comment block above it records
why the US-parity reading was wrong. Consequences, all verified:

- `cog_needs_fx("UK")`: `True` → **`False`**. `cog_currency("UK")`: `USD` → `GBP`.
  US (`False`), CA (`True`) and AU (`True`) are unchanged.
- **No reported number moves.** `reconcile.py` never imports `cog_currency` or `cog_needs_fx`
  *(grep-verified)*, so it structurally cannot be affected. Confirmed empirically: all four reports
  are identical before and after, modulo their generation timestamps.
- The only live consumer is `cogs.py:253`, which writes `pnl_monthly.currency`. On the next
  `sync.cogs --marketplace UK` run the UK `cog` rows will be relabelled `USD` → `GBP` — a
  **correction**, and the mirror image of CA's mislabel in D4.1. Amounts do not change.

**Note on the brief's phrasing.** The task described the target state as "no FX for US/CA/UK".
`cog_needs_fx("CA")` remains `True`, and that is correct: the CA→US override means CA's *effective*
cog really is USD against a CAD pipeline. Nothing converts, deliberately, because Sellerise-CA's
`cog` is USD too (D2.2). Also: "Sellerise reports in native currency too" holds for UK, not for CA —
Sellerise-CA's `cog` is USD-magnitude *(measured: its Σ 8,003.95 sits beside the USD basis 8,324.18,
not the CAD basis 10,600.85)*. That is the whole reason the override exists.

### S6 — `KNOWN_TARGET_DEFECT`

One status, one registry, no new files, no band widened.

- `drift_bands.py:248` — the status constant. `:252` — `TargetDefect(expected_delta, tolerance, note)`
  with a `matches()` predicate. `:553` — `TARGET_DEFECTS`, keyed `(marketplace, month, bucket,
  sub_line)`. `:590` — `target_defect_for()`.
- `classify()` (`:288`) takes an optional defect. A registered cell reads `KNOWN_TARGET_DEFECT` only
  while its Δ sits within tolerance of the measured value, and `INVESTIGATE` otherwise. **It never
  falls back to the band**, so a pinned cell whose Δ moved is a finding even when the new Δ is small
  — including Δ = 0, i.e. the target fixed its bug.
- Sign convention: `expected_delta` is always **ours − theirs**. `reconcile_au.py` renders
  `theirs − ours` and negates before consulting the registry.
- Tolerances are each cell's own measured noise floor, never a fraction of the defect: UK reuses
  `_UK_PRIOR_PULL_BANDS[("cog","(scalar)")]` = $25 (the calibrated pull-to-pull movement); AU uses
  each cell's FX-granularity band ($19.24 / $21.65 / $17.00), and $1.00 for cog, which carries no FX.
- The registry is **not** consulted by the vs-prior-pull guard (`reconcile.py`, comment above
  `drift_vs_prior`). That guard compares our-now to our-then, where a target defect contributes
  nothing; suppressing cells there would blind the one guard that can still catch a code regression
  in them.
- Exit code needed no change: `reconcile.py:1316` already gated on `INVESTIGATE` alone.

**Registered (8 cells, 3 defects):**

| marketplace | month | cell | expected Δ (ours − theirs) | tolerance | defect |
|---|---|---|---:|---:|---|
| UK | 2026-01 | `cog.(scalar)` | +242.84 | ±25.00 | Sellerise understates UK per-SKU cost |
| UK | 2026-02 | `cog.(scalar)` | +177.87 | ±25.00 | ← |
| UK | 2026-04 | `cog.(scalar)` | +184.41 | ±25.00 | ← |
| UK | 2026-05 | `cog.(scalar)` | +122.62 | ±25.00 | ← |
| AU | 2026-01 | `storageFee.storageFee` | +52.75 | ±17.00 | Sellerboard omitted GST from Jan storage |
| AU | 2026-01 | `feesObject.Commission` | +30.07 | ±19.24 | Sellerboard counted 1 of 3 MCF units |
| AU | 2026-01 | `fbaObject.FBAPerUnitFulfillmentFee` | +30.27 | ±21.65 | ← |
| AU | 2026-01 | `cog.(salesCosts)` | −86.71 | ±1.00 | ← |

UK 2026-03 (+29.34) and 2026-06 (+243.54, trailing) carry the same defect but sit inside their
existing bands, so they are not pinned — the band already covers them, and pinning a trailing month
would fight its legitimate movement. Registered in the entry's own note so a reader does not
re-derive it.

**What deliberately was *not* registered.** UK's 5 `fbaObject` cells. At the time of S6 their "Amazon
post-snapshot restatement" label rested entirely on a rate-signature inference with no re-pull ever
run (D3.2 / S2). Registering them would have converted an untested inference into a machine-blessed
"diagnosed defect" and turned the guard green on the strength of nothing. **UK still exits 1.**

*(That restraint was vindicated: S2 ran later the same day and the restatement label turned out to be
**wrong**. Had the cells been pinned to "close" UK, the guard would now be green on a label the
evidence refutes. See § 8.)*

### Results

| marketplace | before | after | exit |
|---|---|---|---:|
| US | 0 INVESTIGATE | 0 INVESTIGATE, 0 pinned | 1 *(unchanged; locked targets 9/15)* |
| CA | 0 INVESTIGATE | 0 INVESTIGATE, 0 pinned | 0 *(unchanged)* |
| UK | **9 INVESTIGATE** | **5 INVESTIGATE** + 4 `KNOWN_TARGET_DEFECT` | 1 *(the 5 were then closed by S2′ — § 8)* |
| AU | 3 CONTENT flags | **0 CONTENT flags** + 3 `KNOWN_TARGET_DEFECT` (+ Jan cog pinned) | 0 *(unchanged)* |

`WITHIN_DRIFT` counts are unchanged on every marketplace: nothing was reclassified into the band.

### Verification

| Check | Method | Result |
|---|---|---|
| pin holds at the measured Δ | `classify` at +242.84, ±24 | `KNOWN_TARGET_DEFECT` |
| pin fires when the defect moves | `classify` at ±26 from expected | `INVESTIGATE` both directions |
| pin fires when the target *fixes* its bug | `classify` at Δ = 0 | `INVESTIGATE` (unpinned it would be `WITHIN_DRIFT`) |
| pin does not widen the band | unregistered cell at Δ = 242.84, band 100 | `INVESTIGATE` |
| AU sign convention | registry rejects −52.75, accepts +52.75 | correct |
| AU cog pin is one MCF unit wide | rejects −173.42 (two units) and 0.00 | correct |
| `cog × 1.20` still fires, US | 6 months, both guards | 5/6 vs-Sellerise, 6/6 vs-prior-pull |
| `cog × 1.20` still fires, CA | 6 months, both guards | 1/6 vs-Sellerise (its band is $500), **6/6 vs-prior-pull** |
| `cog × 1.20` still fires, UK | 6 months, both guards | 6/6 vs-Sellerise, 6/6 vs-prior-pull — incl. all 4 pinned cells |
| no number moved | numeric-token diff of all four reports | US/CA/UK identical; AU identical except the evidence notes |
| reports well-formed | column-count check on every table | 47 tables, all consistent |

CA's cog perturbation is caught only by the vs-prior-pull guard — its vs-Sellerise `cog` band is
$500 against a ~$290/month perturbation. That is pre-existing (the two guards are designed to cover
each other) and unaffected by S6, but it is worth knowing that CA's vs-target cog band is loose.

---

## 8. S2, run — the UK FBA restatement label is refuted

Full workings in [`uk_fba_repull_test.md`](uk_fba_repull_test.md). Read-only: nothing was written to
`sp_transactions`, `sp_breakdowns`, `sp_transaction_items`, `pnl_monthly`, `pnl_monthly_snapshots` or
`sync_state`; the re-pull landed in a scratch file. No band widened, no cell pinned.

### The before-snapshot survived

UK's 2,011 rows in `sp_transactions` carry six distinct `ingested_at` values, one per posted month,
all inside `2026-07-07 07:38:19–07:38:28 UTC`. A single pass, never re-ingested. The stored bytes are
the original pull, so the test could run today against a 3-day interval — days, not the 36 seconds
the earlier "evidence" rested on, but still not the weeks over which restatement accumulates. The
interval is not what carries the refutation.

### Test 1 — Amazon vs Amazon

| | Feb 2026 | Mar 2026 |
|---|---:|---:|
| transactions, stored / fresh | 432 / 432 | 435 / 435 |
| vanished / newly appeared | 0 / 0 | 0 / 0 |
| **byte-identical raw JSON** | **432 / 432** | **435 / 435** |
| `fbaObject` feed, stored → fresh | −673.87 → −673.87 | −657.68 → −657.68 |
| transactions whose FBA total moved | **0** | **0** |

867 transactions, whole raw payload, **£0.00 of movement**. To close Feb the figure would have had to
be ~£117 smaller when Sellerise snapshotted it — a 17 % revision.

### Test 1b — the argument that does not depend on the interval

A restatement would have had to touch the FBA line **and nothing else**, because nothing else
disagrees. On the *same transactions*:

| month | `chargesObject.Principal` Δ | `Commission`+`ReferralFee` Δ | `fbaObject` Δ |
|---|---:|---:|---:|
| 2026-01 | **0.0000** | −118.05 | −71.35 |
| 2026-02 | **0.0000** | 0.00 | −117.25 |
| 2026-03 | **0.0000** | 0.00 | −87.10 |
| 2026-04 | **0.0000** | 0.00 | −60.35 |
| 2026-05 | **0.0000** | 0.00 | −61.20 |
| 2026-06 | **0.0000** | 0.00 | −61.20 |
| **Σ** | **0.0000** | −118.05 | **−458.45** |

Revenue agrees with Sellerise's frozen snapshot to the cent, every month. Amazon revising a fee line
by 9.6–23.6 % while leaving the principal on those same transactions identical to the penny is not a
credible mechanism. **Label refuted.**

### Test 2 — the netting hypothesis, also refuted as the explanation

- **There are no FBA-fee refund leaves to net.** Zero `Refund`-side FBA leaves anywhere in UK Jan–Jun;
  Amazon does not reverse the fulfilment fee on a return. Sellerise's `refundsObject` has no FBA line
  either — its keys are identical to ours — and no other Sellerise bucket carries one.
- Reconstructing the fee Amazon *actually charged* on each refunded unit (matched on `order_id` +
  `sku`, 69 of 78 units matched) and deducting it: Σ\|Δ\| 458.45 → **194.12** (refund posted-month) or
  **225.68** (purchase-month). Closes ≤ 58 % and leaves a same-signed residual of ≈ −£147.
- Eliminated alongside: FBA fees on zero-revenue items (**none exist** — no replacements/MCF), and
  misclassification into `expenses` (Sellerise's reimbursement and inbound lines reconcile to our
  leaves **exactly**, Jan–Apr).

### What is actually true

Identical shipment set. On those units, Amazon charged £3.53–3.86/unit; Sellerise's implied rate is
£2.76–3.34 — 9.6–23.6 % lower, and *less* stable month to month than ours (CV 6.7 % vs 4.2 %). A single
scalar `theirs ≈ 0.8391 × ours` describes 76 % of it, which is a description, not a mechanism.

**Sellerise's `fbaObject` is not a sum of Amazon's charged FBA fees.** That is the same shape as UK's
cog residual — our per-unit value above Sellerise's, on one of the two lines Sellerise *derives* per
unit rather than reading from the feed — and it carries the same limitation: Sellerise exposes only a
monthly aggregate, so its per-unit FBA rate cannot be observed from anything in this repo (D3.5).

### Interim verdict (S2)

> Not restatement. Not netting. At this point the −£458.45 was **`UNEXPLAINED`, same-signed**, the
> five cells stayed `INVESTIGATE`, and UK still exited 1. A same-signed material residual stays
> systematic until a test names it.

---

## 8b. S2′ — the residual is named: Sellerise omits GMAKER-3's FBA fee

The discriminating experiment was one SKU. Sellerise's own per-unit FBA fee for **GMAKER-3**: £27.75
across **142 units**, Jan–Jun. Our unit count for the same SKU and window, on the same purchase-date
basis: **142**. The two sides are describing the same units.

### The shortfall

| | Amazon (charged, from `sp_transactions`) | Sellerise | shortfall |
|---|---:|---:|---:|
| total FBA, GMAKER-3, Jan–Jun | **−£479.15** | −£27.75 | **£451.40** |
| units | 142 | 142 | — |
| **£/unit** | **3.374** | **0.195** | **94.2 % understated** |

£451.40 against a £458.45 gap — **98.5 %** of the entire `fbaObject` residual, from one SKU.

### It reconciles month by month, to the penny

| month | `fbaObject` bucket gap | GMAKER-3's Amazon fee | difference |
|---|---:|---:|---:|
| 2026-01 | −71.35 | −71.35 | **0.00** |
| 2026-02 | −117.25 | −117.25 | **0.00** |
| 2026-03 | −87.10 | −87.10 | **0.00** |
| 2026-04 | −60.35 | −81.05 | +20.70 |
| 2026-05 | −61.20 | −61.20 | **0.00** |
| 2026-06 | −61.20 | −61.20 | **0.00** |
| **Σ** | **−458.45** | **−479.15** | **+20.70** |

**In five of six months the whole UK FBA residual *is* GMAKER-3's fulfilment fee.** Sellerise books
nothing for it. April is the sole exception — it booked exactly £20.70 there, and that £20.70 is the
entire six-month difference. Implied Sellerise booking for the SKU: £0.00 × 5 months + £20.70 = £20.70,
against the £27.75 it reports; the £7.05 remainder is **0.27 %** of the ~£2,600 non-GMAKER-3 FBA base.
Rounding.

This also disposes of the one loose end from S2 — Sellerise's implied per-unit rate looked *less*
stable than ours (CV 6.7 % vs 4.2 %), which no fixed rate table can produce. It is our figure with one
SKU zeroed out, and GMAKER-3's share of monthly units swings from 10 % to 25 %.

### Every pinned Δ decomposes into two named components

The guard cells sit on `fbaObject.FBAPerUnitFulfillmentFee`, not on the bucket. The difference is
Sellerise's `FBAFees` line — its deferred-shipment estimate, for which we have no counterpart now that
those shipments have released.

| month | GMAKER-3's omitted fee | Sellerise's `FBAFees` estimate | sum | cell Δ in the report |
|---|---:|---:|---:|---:|
| 2026-01 | −71.35 | −8.71 | −80.06 | **−80.06** |
| 2026-02 | −117.25 | −17.84 | −135.09 | **−135.09** |
| 2026-03 | −87.10 | −8.93 | −96.03 | **−96.03** |
| 2026-04 | −60.35 | 0.00 | −60.35 | **−60.35** |
| 2026-05 | −61.20 | −3.10 | −64.30 | **−64.30** |

No unexplained remainder anywhere.

### Pinned

Five settled cells in `drift_bands.TARGET_DEFECTS`, tolerance **±£15** — reused from
`_UK_PRIOR_PULL_BANDS[("fbaObject","FBAPerUnitFulfillmentFee")]`, the calibrated pull-to-pull movement
for that cell, never a fraction of the defect. `2026-06` carries the same defect but is trailing and
still moving; a trailing month is never pinned.

| marketplace | before | after | exit |
|---|---|---|---:|
| US | 0 INVESTIGATE | unchanged | 1 *(locked targets 9/15, pre-existing)* |
| CA | 0 INVESTIGATE | unchanged | 0 |
| **UK** | **5 INVESTIGATE + 4 pinned** | **0 INVESTIGATE + 9 pinned** | **0** ← first green run |
| AU | 3 pinned | unchanged | 0 |

`WITHIN_DRIFT` (149) and `TRAILING` (30) are unchanged for UK: nothing was reclassified into a band,
and **no band was widened**. US, CA and AU reports are byte-identical; UK's per-cell diff tables (164
rows) are byte-identical too — only statuses moved.

### The pin holds; it does not excuse

| check | result |
|---|---|
| Δ at the measured value | `KNOWN_TARGET_DEFECT` |
| Δ ±£14 (inside tolerance) | `KNOWN_TARGET_DEFECT` |
| Δ ±£16 (moved) | `INVESTIGATE`, both directions |
| **Δ → 0.00, i.e. Sellerise fixes the SKU** | **`INVESTIGATE`** (unpinned it would read `WITHIN_DRIFT`) |
| unregistered cell at the same Δ, band 50 | `INVESTIGATE` — the pin widens nothing |
| `fbaObject × 1.20`, all 5 cells | `INVESTIGATE` on both guards |
| one extra GMAKER-3 unit's fee (£3.37) | still `KNOWN_TARGET_DEFECT` — tracks the defect, not noise |
| five extra units (£16.87) | `INVESTIGATE` |
| `cog × 1.20` regression test | still fires on US / CA / UK |

### Consequences (→ S2″)

1. The Δ **scales with GMAKER-3's monthly volume**, so each new settled month needs its own entry.
2. **If Sellerise corrects the fee, these cells fire `INVESTIGATE`** — by design. That is the signal to
   delete the entries, and the only clean way this ends.
3. **Do not adjust our FBA figure.** It is the fee Amazon billed, straight off the
   `FBAPerUnitFulfillmentFee` leaves. Do not widen the band, do not touch the `fbaObject` mapping.

### Code changed

`drift_bands.py` only: the five registry entries, their evidence note, `_UK_FBA_TOL`, and the UK-band
comment (which no longer asserts the refuted restatement label). No other file, no behavioural change
outside the intended reclassification.

### The sequence is the point

The label was **refuted before the cause was found**, and the cells were held at `INVESTIGATE` in
between. Had they been pinned to the restatement label to make UK green, the guard would now be
certifying a claim the evidence kills — and the real defect, sitting in one SKU's fee, would never
have been looked for.

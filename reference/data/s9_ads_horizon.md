# S9 — extending the ingestion horizon to ad_spend_daily (AU)

Run 2026-07-10. Read-only against the production tables (all writes went to `*_s9` scratch copies);
no reported number moved; exit codes unchanged (US 1 pre-existing, CA 0, UK 0, AU 0).

> ## Two findings, in order of importance
>
> **1. `as_of` is a pull timestamp, but it is NOT a horizon** — because `_replace_month` deletes and
> reinserts, the pre-restatement value is physically gone. This is **Step 2b**. Fixed by keeping the
> superseded rows in a small append-only `ad_spend_history` table; the horizon reconstructs a cell from
> `[as_of, superseded_at)` validity intervals. Verified exact to the cent against the real backup.
>
> **2. The false positive S9 was built to prevent essentially cannot occur for the current AU cells.**
> AU's FX reference rate is the **median** of its content-insensitive anchors — two refunds and ads —
> and a median is robust to any single anchor by design. A 10× or a 0.01× January ads restatement moves
> the rate by at most the refund-anchor spread (0.0001), i.e. **£0.15 on a pinned cell against a £19.24
> tolerance — ~127× headroom.** So the S8-noted gap was not merely "a wide margin": the FX design
> already makes AU pins ads-robust. The horizon extension is still correct and worth keeping (it
> completes the guarantee uniformly, and a future refund-less pinned month would not be robust), but the
> "ads pushes a pin past tolerance" scenario is vacuous for the January cells that exist today.

---

## Step 1 (gate) — is `as_of` usable as a horizon?

`ads_spend.py` sets `as_of = dt.datetime.now(dt.timezone.utc)` at write time (`sweep_ad_spend`), once
per pull. So it **is** a pull timestamp — Step 2a's precondition.

But that is not sufficient, because `_replace_month` is **replace-in-place**: it `DELETE`s a
`(marketplace, month)` and reinserts. A restatement therefore *overwrites* the prior row at the same
PK, and the old value is gone. Filtering the live table on `as_of <= H` cannot reconstruct the
pre-restatement state — it can only drop the newer row, leaving that campaign-day **missing**, which
understates the month.

**Proof, from the live table:** the blockers task re-pulled Jan–May on 2026-07-10. Today, **zero** rows
for those months carry the old `as_of <= 2026-07-08` — the 2026-07-07 values are physically gone:

| month | `as_of` in the 2026-07-07 backup | `as_of` in the table now |
|---|---|---|
| 2026-01 | 2026-07-07 03:16:29 | 2026-07-10 13:29:07 |
| 2026-02 | 2026-07-07 03:16:32 | 2026-07-10 13:15:56 |
| … | … | … |

So `as_of` is a pull timestamp that **cannot serve as a horizon on the live table alone**. → **Step 2b.**

---

## Step 2b — keep the superseded rows

The smaller of the two sanctioned options (add `ingested_at` + stop replacing vs. record replaced rows):
**record replaced rows.** It leaves `ad_spend_daily`, its PK, and every reader untouched; it is purely
additive.

- **`ad_spend_history`** (migration `f6a7b8c9d0e1`): the `ad_spend_daily` columns plus `superseded_at`.
  Each row records the version that was live during `[as_of, superseded_at)`.
- **`_replace_month`** snapshots the to-be-deleted rows into history with `superseded_at = as_of` (the
  new pull's timestamp — the instant they stop being current) **before** the `DELETE`. Gated on the
  real table, so scratch verification runs never touch history.
- **`load_au_ad_spend(conn, ingested_before=H)`** reconstructs: a live row if it was already current at
  `H` (`as_of <= H`), else the historical version whose interval contains `H`
  (`as_of <= H < superseded_at`). The two are mutually exclusive per PK, so a plain `UNION ALL` is
  correct even across multiple restatements. On the normal path (`None`) it is the live query, unchanged.

Only `load_au_ad_spend` needs the horizon — AU is the only ads-anchored marketplace. `_build_rows`
re-reads ad spend at the horizon (it feeds the FX rate), and `_as_of_deltas` drives it.

### A latent bug S9 forced out: `measured_at` predated the ad re-pull

S8 set every pin's `measured_at` to `2026-07-10T00:00:00Z`, correct for the tables it horizoned
(`sp_transactions` max `2026-07-07`, `order_purchase_date` max `2026-07-09`). But the Jan–May ads were
re-pulled at `2026-07-10T13:xx` — **after** that horizon. Extending the horizon to ads at midnight would
have excluded the current AU ad rows on every run, breaking the "no-op when nothing was ingested"
guarantee. Corrected to `2026-07-10T23:59:59Z`, which sits after all three tables' latest stamps.
Verified: `load_au_ad_spend(ingested_before=pin_horizon)` is identical to the live query, month by month.

---

## Step 3 — verification

All against the **real** Step-0 backup (the 2026-07-07 pull), through the **real** `_replace_month`
history path and the **real** `load_au_ad_spend` reconstruction, on scratch tables.

### The reconstruction is exact

| check | result |
|---|---|
| AU June restated −£10.00 via `_replace_month`; history captured the superseded rows | ✓ |
| AU June at a **pre**-restatement horizon | reconstructs the **original** £729.95 |
| AU June at a **post**-restatement horizon | reconstructs the **restated** £719.95 |
| AU January restated ×2 (+£1,272 → the sum doubles) | at the pin horizon, reconstructs the **original** £1,272.11 |

### The FX median makes AU pins ads-robust (the second finding)

`feesObject.Commission` is pinned +30.07 ±19.24. Its Δ under every ads restatement magnitude:

| January ads | pinned Δ moves to | moved by |
|---|---:|---:|
| ×1 (baseline) | +30.07 | 0.002 |
| ×3 | +30.22 | 0.152 |
| ×10 | +30.22 | 0.152 |
| ×0.1 | +30.07 | 0.002 |
| ×0.001 | +30.07 | 0.002 |

**Worst movement 0.152 against a 19.24 tolerance — ~127× headroom.** The reference rate is
`0.6736` and never moves beyond `0.6735–0.6736`, because January's insensitive anchors are two refunds
(0.6735, 0.6736) and ads (0.6790, the high outlier); the median is set by the refunds and ads is one
robust-against vote. No ads restatement, however large, can push these cells past tolerance.

### The DEFECT_REMEASURED-via-ads path works end to end

Because the real tolerances can't be crossed by ads, the full path is exercised with a **tight
back-dated pin** (±0.05) so the real, tiny, ads-induced movement crosses it — the *mechanism*
(reconstruct ad spend from history at the horizon → recover the pre-restatement Δ → classify) is exactly
production:

| step | value |
|---|---|
| pin +30.0683 ±0.05 at horizon 2026-07-15; ads ×10 restated after it | current Δ +30.2219 |
| Δ at horizon, from the real history reconstruction | **+30.0683** = the pin |
| classify | **`DEFECT_REMEASURED`** |

### Teeth intact

| check | result |
|---|---|
| code change (current **and** as-of Δ move) | `INVESTIGATE` |
| no-ingest run (as-of Δ == current Δ) | `DEFECT_REMEASURED` unreachable |
| S8 tests (KTD, FBA pin, cog×1.20 / fbaObject×1.20, back-dated integration) | all pass |
| horizon at the pin is a no-op | AU ad spend identical, month by month |
| all four reports vs the pre-S8 baseline | every numeric token identical, in order |

### Defensive guard

A horizon early enough for a month to lose all its FX anchors cannot happen for a correctly-set pin
(`measured_at` is always after all ingested data — verified). If a mis-set `measured_at` ever produced
one, `_as_of_deltas` now catches the `SellerboardParseError`, logs it, and leaves those cells without an
as-of Δ — so they read `INVESTIGATE`, not a crash. An unattended cron degrades to "alarm," never to
"dead."

---

## Code changed

- **migration `f6a7b8c9d0e1`** — `ad_spend_history` (additive).
- **`ads_spend.py`** — `AD_SPEND_HISTORY_TABLE`; `_replace_month` snapshots superseded rows before
  delete (gated on the real table); `sweep_ad_spend`/CLI thread `history_table`.
- **`reconcile_au.py`** — `load_au_ad_spend(ingested_before=...)` reconstructs from history;
  `_build_rows` re-reads ad spend at a horizon; `_as_of_deltas` gains the defensive guard.
- **`drift_bands.py`** — `measured_at` corrected to end-of-day (after the ad re-pull).

No reconciliation math, attribution, bucket map, band, tolerance, or `aggregate_marketplace` return
shape touched. No band widened. `ad_spend_daily` is byte-for-byte the Step-0 backup; `ad_spend_history`
is empty (no real restatement occurred).

## Recommendation

Keep the horizon extension — it makes the as-of reconstruction cover **every** input to an AU cell, so
the guarantee is uniform rather than "ads probably doesn't matter." But record the second finding as the
operative one: **for the current AU pins, the median FX rate already prevents an ads restatement from
crossing tolerance, by ~127×.** The S8 gap is closed both ways — the mechanism now handles it, and the
FX design means it was never going to fire. If a future pinned month is refund-less (falling back to the
all-anchor rate, where ads carries real weight), this horizon is what keeps it safe.

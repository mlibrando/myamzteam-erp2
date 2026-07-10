# Unit COG Comparison — workbook vs Sellerise-implied per SKU

Generated 2026-07-07. Diagnostic only — no values edited.

> **SUPERSEDED CONCLUSIONS — the measurements below stand; two of the verdicts drawn from them do not.**
> Body text is left exactly as written. See [`decisions_audit.md`](decisions_audit.md).
>
> **1. The UK verdict is inverted (§ Summary verdict, "pipeline HIGH"; § Findings 1; § 6).**
> "Workbook costs systematically above Sellerise" and "Sellerise understates the workbook" are the
> *same measurement*. A two-sided comparison cannot say which side is right. The **component cost
> build-up** can, and it validates the sheet: ABDB 78.53, GMAKER-3 30.94, MBUKB1 96.06 all tie out
> against per-component invoice cost. Sellerise understates ABDB and MBUKB1; it matches GMAKER-3.
> **Correct classification: a Sellerise-side data defect (`KNOWN_TARGET_DEFECT`), the UK analogue of
> Sellerboard's AU GST omission — not a data-governance action on our side.**
> Do **not** edit the UK workbook. Do **not** "correct" our cog to match Sellerise's implied values
> (§ Findings 1, § Summary verdict last paragraph). Doing so would import the target's error.
>
> **2. The CA verdict ("a pure US×1.35 artifact") is wrong about the cause, right about the action.**
> The ×1.35 is a **genuine CAD markup** — the CA sheet is denominated in CAD, and CAD/USD ≈ 1.35.
> Note the CA *retail* column is US × 1.1440, a different multiplier: a mechanical FX artifact would
> have produced one multiplier for both columns. The pipeline still correctly joins the US sheet,
> but because that puts a **USD cog against Sellerise-CA's USD `cog` field** — not because the CA
> sheet is bogus. Real CA-sourced costs landing in the sheet would make the override *more*
> necessary, not less. See `config.py`'s `MARKETPLACE_COG_SOURCE_OVERRIDE`.
>
> **3. The per-SKU `implied cog` column (§ UK — per-SKU dollar impact) is not a per-SKU measurement.**
> It is proportional attribution, which the doc states at § "Assumption: all SKUs are off by the same
> relative fraction". By construction it assigns every SKU the same −5.06 % gap; the resulting
> ABDB $74.56 and MBUKB1 $91.20 are outputs of that assumption, not observations of Sellerise's
> values. Sellerise's API exposes only monthly aggregate `cog` (§ Method, "Limitation"), so **no
> per-SKU Sellerise unit cost is observable from this repo at all.**

## Purpose

Sellerise computes COGS as `(units_sold − units_refunded) × unit_COG` — a single per-unit cost
per SKU. Any COGS residual between our pipeline and Sellerise is purely a **per-unit cost-value
disagreement**. This report quantifies that gap per SKU so the DMS gets exact deltas, not
estimates.

## Method

**Data sources:**
- `COGS_Magical_Butter_1.xlsx` (US, UK, CA sheets) for workbook unit costs.
- `SELLERISE_RAW_DATA_UK.json`, `_CA.json`, `_US.json` for monthly aggregate cog totals.
- `reference/data/rollout_probe/UK_*.json` and `CA_*.json` for per-SKU unit volumes.
- `reconcile_report_UK.md`, `_CA.md`, `_US.md` for pipeline-accurate monthly cog figures.

**Limitation:** Sellerise's API exposes only monthly aggregate cog, not per-SKU breakdown.
Back-calculating per-SKU unit costs from aggregate data is a mathematically underdetermined
system (14 UK SKUs, 6 monthly equations). Rather than an unphysical minimum-norm LS solution,
this report uses two independent signals:

1. **UK/US reference ratio**: match UK and US workbook entries by ASIN; the ratio isolates which
   UK costs diverge from the US baseline.
2. **Proportional attribution**: distribute the total cog residual by each SKU's share of
   posted-date pipeline cost. Assumes the error is uniform per unit — a simplification, but it
   ranks SKUs by dollar exposure honestly.

Transaction volumes use RELEASED-status transactions (posted-date) as a proxy for pipeline
purchase-date attribution. Totals differ from the reconcile-report figures by ~7% due to timing.

---

## US Control — monthly cog sanity check

Pipeline cog matches Sellerise within ±2% per month; overall the residual is −2.1% (pipeline
under-attributes vs Sellerise). This is **not** the same sign as UK (+5.76%), confirming UK has
a distinct systematic driver, not just generic attribution noise.

| month   | Sellerise     | Pipeline      | Δ          | Δ %   |
|---------|--------------|--------------|-----------|-------|
| 2026-01 | 45,968.20    | 43,949.37    | −2,018.83 | −4.4% |
| 2026-02 | 34,647.26    | 33,733.32    | −913.94   | −2.6% |
| 2026-03 | 29,423.96    | 28,959.59    | −464.37   | −1.6% |
| 2026-04 | 30,790.78    | 30,607.83    | −182.95   | −0.6% |
| 2026-05 | 27,180.01    | 26,687.33    | −492.68   | −1.8% |
| 2026-06 | 25,073.27    | 25,084.70    | +11.43    | +0.0% |
| **Σ**   | **193,083.48** | **189,022.14** | **−4,061.34** | **−2.1%** |

US cog residuals are not mixed-sign (mostly negative), but US overall net reconciles at +1.7%
because other items (revenue timing, fees) over-compensate. **Control verdict: US workbook unit
costs are ~2% below Sellerise's implied values — direction is opposite to UK, consistent with
independent, not mechanically linked, cost entries.**

---

## CA Control — monthly cog check

CA uses the US cog source (`MARKETPLACE_COG_SOURCE_OVERRIDE`). CA cog residuals are
**mixed-sign** with a small net (+$197.57, +2.47% of Sellerise), confirming the cog override fix
is working correctly.

| month   | Sellerise  | Pipeline   | Δ        |
|---------|-----------|-----------|---------|
| 2026-01 | 1,587.21  | 1,445.51  | −141.70 |
| 2026-02 | 1,881.36  | 1,676.52  | −204.84 |
| 2026-03 | 1,454.84  | 1,622.51  | +167.67 |
| 2026-04 |   653.28  |   643.95  |   −9.33 |
| 2026-05 |   894.10  | 1,222.02  | +327.92 |
| 2026-06 | 1,533.16  | 1,591.01  |  +57.85 |
| **Σ**  | **8,003.95** | **8,201.52** | **+197.57** |

### CA workbook vs US source (reference only — CA sheet is NOT used in pipeline)

Every CA workbook entry is exactly **1.350× the US entry** for the same SKU — this is the
pre-fix CA cog bug (US×1.35 multiplier). The pipeline correctly ignores the CA sheet and uses
US costs directly.

| SKU               | ASIN          | CA workbook | US source | CA/US ratio |
|-------------------|---------------|------------|----------|------------|
| MBDBOX1           | B0CX1XSLV7   | 82.80      | 61.33    | 1.350×     |
| 850251005008      | B014GNGTBK   | 66.11      | 48.97    | 1.350×     |
| AMZBBB            | B084BYD6JN   | 83.77      | 62.05    | 1.350×     |
| JU-L51X-ZVP2      | B09TLGP2XP   | 9.86       | 7.30     | 1.351×     |
| GMAKER-3          | B0DDL84DNV   | 41.53      | 30.76    | 1.350×     |
| 83-EFO4-1SGB      | B088TWCGKL   | 8.15       | 6.04     | 1.349×     |
| UP-EMO2-CQK5      | B08CVW3W8X   | 5.04       | 3.73     | 1.351×     |
| OQ-XCHS-529Y      | B0892SP4NT   | 8.91       | 6.60     | 1.350×     |
| M1-SI1M-DCLU      | B0892S6WPD   | 13.44      | 9.96     | 1.349×     |
| IF-9JB7-NA1T      | B088TV9BX7   | 8.14       | 6.03     | 1.350×     |
| P4-KG72-Q6TL      | B08CLVRLYL   | 9.38       | 6.95     | 1.350×     |

**Conclusion: CA sheet is a pure US×1.35 artifact and should remain unused in the pipeline.**

---

## UK — monthly cog residual

UK pipeline over-attributes cog vs Sellerise every month (consistent positive sign).
Total residual +$1,000.62 over Jan–Jun = **+5.76% of Sellerise UK cog**.

| month   | Sellerise  | Pipeline   | Δ (over) |
|---------|-----------|-----------|---------|
| 2026-01 | 3,145.54  | 3,388.38  | +242.84 |
| 2026-02 | 3,859.36  | 4,037.23  | +177.87 |
| 2026-03 | 3,300.51  | 3,329.85  |  +29.34 |
| 2026-04 | 3,295.13  | 3,479.54  | +184.41 |
| 2026-05 | 1,645.00  | 1,767.62  | +122.62 |
| 2026-06 | 2,121.51  | 2,365.05  | +243.54 |
| **Σ**  | **17,367.05** | **18,367.67** | **+1,000.62** |

Average over-attribution: **+$1.21/unit** (827 estimated RELEASED-status units Jan–Jun).

---

## UK — per-SKU: workbook COG vs US reference

All values in USD (pipeline treats workbook as USD regardless of currency denomination in
the spreadsheet). Ratios compare UK workbook to US workbook for the same ASIN.

| SKU              | ASIN          | UK workbook | US reference | UK/US  | product                              |
|------------------|---------------|------------|-------------|--------|--------------------------------------|
| ABDB             | B09NP5KWQ6   | 78.53      | —           | n/a    | MB2E + Decarbox bundle (UK-exclusive) |
| GMAKER-3         | B0DDL84DNV   | 30.94      | 30.76       | 1.006× | Gummy Maker                          |
| MBUKB1           | B0CX1WMVQV   | 96.06      | —           | n/a    | MB2E + Decarb + BT + Molds (UK-exclusive) |
| O1-2Z9F-AKL9     | B09TLGP2XP   | 7.40       | 7.30        | 1.014× | Filter Press                         |
| MBUKB2           | B0CX1XRBVV   | 79.28      | —           | n/a    | MB2E + Cups + 2mL Mold (UK-exclusive) |
| GH-4JLG-DAOW     | B08CVWBKV8   | 4.26       | 3.73        | 1.142× | 21UP Butter Mold                     |
| S2-5MCK-YDGH     | B08CVW3W8X   | 3.83       | 3.73        | 1.027× | Butter Mold                          |
| 4C-76GT-VAWZ     | B0892SP4NT   | 6.70       | 6.60        | 1.015× | 10mL Gummy Mold                      |
| T9-U023-1I57     | B088TV9BX7   | 6.34       | 6.03        | 1.051× | 8mL Gummy Mold                       |
| YU-6N3V-OEQW     | B08CLVRLYL   | 7.00       | 6.95        | 1.007× | 3-Pack Silicone Cups                 |
| 87-B4TQ-CWM8     | B088TWCGKL   | 6.31       | 6.04        | 1.045× | 2mL Gummy Mold                       |
| 09-S0XE-7G6I     | B07518MK6N   | 12.56      | 12.36       | 1.016× | Decarbox (standalone)                |
| MT-XOGP-1VU6     | B0892S6WPD   | 15.84      | 9.96        | **1.590×** | Spatulas                         |
| B5-FUC0-5AKB†    | B088TWCGKL   | —          | 6.04        | n/a    | 2mL Gummy Mold **[MISSING from UK workbook]** |

† B5-FUC0-5AKB: 74 units sold Jan–Apr, same ASIN as 87-B4TQ-CWM8. Pipeline cost = $0
(missing entry). Adding at $6.31/unit would increase pipeline cog by ~$467, making the
residual **larger**, not smaller. Leave out until DMS confirms correct cost basis.

**UK/US ratio summary:**
- SKUs with US reference: range 1.006×–1.590× (median ~1.030×).
- UK bundles (ABDB, MBUKB1, MBUKB2): no US equivalent — costs must be verified against
  actual UK procurement receipts.
- MT-XOGP-1VU6 (Spatulas): 1.590× US is the largest ratio, but only 2 units sold → negligible
  dollar impact.
- GMAKER-3: 1.006× US (essentially parity) — its large proportional dollar share below is due
  to volume, not a per-unit pricing gap.

---

## UK — per-SKU dollar impact (ranked)

Residual distributed proportionally by each SKU's share of pipeline cost.
**Assumption: all SKUs are off by the same relative fraction** — this is a simplification.
The UK/US ratio column above gives a more direct, assumption-free signal for which SKUs
diverge from US pricing.

| SKU              | UK workbook | US ref | UK/US  | est.units | $pipeline | $resid (prop.) | Δ/unit  | implied cog |
|------------------|------------|--------|--------|----------|-----------|----------------|---------|-------------|
| ABDB             | 78.53      | —      | n/a    | 121      | 9,502     | +480           | +3.97   | 74.56       |
| GMAKER-3         | 30.94      | 30.76  | 1.006× | 130      | 4,022     | +203           | +1.56   | 29.38       |
| MBUKB1           | 96.06      | —      | n/a    | 29       | 2,786     | +141           | +4.86   | 91.20       |
| O1-2Z9F-AKL9     | 7.40       | 7.30   | 1.014× | 196      | 1,450     | +73            | +0.37   | 7.03        |
| MBUKB2           | 79.28      | —      | n/a    | 8        | 634       | +32            | +4.01   | 75.27       |
| GH-4JLG-DAOW     | 4.26       | 3.73   | 1.142× | 88       | 375       | +19            | +0.22   | 4.04        |
| S2-5MCK-YDGH     | 3.83       | 3.73   | 1.027× | 77       | 295       | +15            | +0.19   | 3.64        |
| 4C-76GT-VAWZ     | 6.70       | 6.60   | 1.015× | 36       | 241       | +12            | +0.34   | 6.36        |
| T9-U023-1I57     | 6.34       | 6.03   | 1.051× | 33       | 209       | +11            | +0.32   | 6.02        |
| YU-6N3V-OEQW     | 7.00       | 6.95   | 1.007× | 14       | 98        | +5             | +0.35   | 6.65        |
| 87-B4TQ-CWM8     | 6.31       | 6.04   | 1.045× | 14       | 88        | +4             | +0.32   | 5.99        |
| 09-S0XE-7G6I     | 12.56      | 12.36  | 1.016× | 5        | 63        | +3             | +0.63   | 11.93       |
| MT-XOGP-1VU6     | 15.84      | 9.96   | **1.590×** | 2    | 32        | +2             | +0.80   | 15.04       |
| B5-FUC0-5AKB†    | 0.00       | 6.04   | n/a    | 74       | 0         | +0             | n/a     | n/a         |
| **TOTAL**        |            |        |        | **827**  | **19,796** | **+1,001**    | **+1.21** |           |

*Units are RELEASED-status posted-date estimates. Pipeline $-attributed total ≈ $19,796 vs
reconcile-accurate $18,368 (7% difference due to purchase-date attribution).*

---

## Findings and DMS action items

### 1. UK bundles — no US cross-check available (priority: HIGH)

ABDB, MBUKB1, MBUKB2 are UK-exclusive bundles. Together they account for **62% of the
proportional residual** ($653/$1,001). Their workbook values ($78.53, $96.06, $79.28) cannot
be validated against a US reference. The DMS should compare each against:
- Actual UK invoice cost per component
- Sellerise's internal COG entry for each ASIN (if accessible)

The proportional method implies ABDB should be ~$74.56 and MBUKB1 ~$91.20 per unit to
zero the cog residual (all else equal).

### 2. GMAKER-3 — volume driver, not a per-unit problem (priority: LOW)

GMAKER-3 accounts for 20% of the proportional residual purely from volume (130 units).
Its UK/US ratio is 1.006× — essentially identical to US. The $1.56/unit implied gap is
an artifact of proportional spreading, not evidence of a mispriced workbook entry.
**Do not adjust GMAKER-3 on the basis of this analysis.**

### 3. GH-4JLG-DAOW — moderate over-pricing vs US reference (priority: MEDIUM)

UK 4.26 vs US 3.73 = 1.142× (14.2% premium). With 88 units, proportional attribution
gives ~$19 residual contribution. The UK/US difference ($0.53/unit) is real and consistent
with the ratio pattern — UK price for this SKU was entered about 14% above the US equivalent.
Recommend: verify against UK procurement cost and adjust if no UK-specific cost driver exists.

### 4. MT-XOGP-1VU6 — largest ratio, negligible impact (priority: LOW)

1.590× US ($15.84 vs US $9.96) — the biggest workbook discrepancy by percentage. But only
2 units sold Jan–Jun → $2 total proportional impact. Worth correcting the workbook for
accuracy, but will not measurably move the cog residual.

### 5. O1-2Z9F-AKL9 — high volume, low ratio (priority: LOW)

196 units (highest volume) at 1.014× US ($7.40 vs $7.30 = $0.10/unit difference).
Proportional attribution gives +$0.37/unit, $73 total. The UK/US ratio suggests this is
correctly priced; the $73 proportional share is volume noise.

### 6. Missing SKU B5-FUC0-5AKB — leave as-is (confirmed)

74 units, ASIN B088TWCGKL (same as 87-B4TQ-CWM8). Adding to workbook at $6.31/unit
would add ~$467 to pipeline cog, increasing the residual, not reducing it. This implies
Sellerise already has these units priced above $6.31 in its own cog. Leave out until
the bundle-ABDB vs standalone discrepancy is resolved.

---

## Summary verdict

| marketplace | cog residual Σ | direction     | cause                                    |
|------------|---------------|---------------|------------------------------------------|
| US         | −$4,061 (−2.1%) | pipeline LOW  | workbook costs modestly below Sellerise  |
| CA         | +$198 (+2.5%)  | mixed-sign    | US override working; small remaining noise |
| UK         | +$1,001 (+5.8%) | pipeline HIGH | workbook costs systematically above Sellerise; concentrated in UK-exclusive bundles (ABDB, MBUKB1, MBUKB2) |

UK's +$1,001 cog over-attribution directly explains ~63% of the −$1,594 net deficit
(the remaining 37% is fbaObject Amazon post-snapshot restatement, unfixable at pipeline level).

Correcting the UK bundle workbook costs to match Sellerise's implied values would collapse
most of the INVESTIGATE alerts that currently fire on the `cog.(scalar)` cell.

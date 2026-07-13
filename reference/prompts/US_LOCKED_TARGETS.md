# Claude Code Task — Resolve US's permanent exit 1 (locked targets 9/15) before the cron runs

## Context

`reconcile --marketplace US` exits **1** on "locked targets 9/15." It is pre-existing and every
other marketplace exits 0. This was harmless while runs were manual. **It stops being harmless the
moment US is on a cron:** if US is red every single run for a reason nobody acts on, the one signal
that means "go look" becomes background noise, and the whole guard architecture gets trained into
being ignored. Resolve it before go-live.

**This is a diagnosis-first task.** The goal is to decide, per locked target, whether it is
*accepted-and-explainable* (→ give it a status so US can exit 0 honestly) or *genuinely unresolved*
(→ it must be closed, not silenced). Do not just flip the exit condition.

## Operating rules

- **Simplicity.** Understand what "locked targets 9/15" means, classify the 9, act minimally. No new
  framework, no reclassification of the guard system.
- **Do not silence to go green.** Making US exit 0 by loosening the gate, without understanding the 9,
  is exactly the failure this task exists to prevent. A green run must mean something.
- Change no reconciliation math, attribution, bucket maps, bands, tolerances, or reported numbers.

## Step 1 — Establish what "locked targets 9/15" actually is

- Find where the exit code is gated on locked targets and what a "locked target" is (a pinned expected
  value? a golden figure the reconcile checks itself against?). Report the mechanism plainly — this is
  a different construct from the drift guards and `KNOWN_TARGET_DEFECT`, and it must not be conflated
  with them.
- List the 15 targets and identify which 9 are failing, with each one's expected vs actual and the Δ.

## Step 2 — Classify each of the 9 failing targets

For each, decide by evidence which bucket it falls in:

- **Stale target** — the locked expected value predates a fix that legitimately changed the number
  (e.g. the refund-COGS netting, purchase-date attribution, the ads loader reproduction). The current
  number is correct; the locked target is out of date. → the target should be **updated** to the
  current correct value, with a note saying which fix moved it.
- **Known target-side defect** — the same class already handled elsewhere (Sellerise/Amazon is wrong,
  our number is right). → it should carry the same kind of documented, expected status, not a hard fail.
- **Genuinely unresolved** — the number is actually wrong, or unexplained. → it must be **closed**
  (named by test like every other residual in this project), not silenced. If closing it is a real
  investigation, stop and report it as a blocker rather than papering over it.

Report the 9 as a table: target, expected, actual, Δ, classification, evidence.

## Step 3 — Act minimally per classification

- **Stale** → update the locked expected value to the current correct number; record why (which fix).
- **Known defect** → give it the existing documented-expected treatment so it does not hard-fail, with
  its evidence note. Reuse the mechanism already in place; do not invent a parallel one.
- **Unresolved** → do **not** resolve it by fiat. Report it. If any of the 9 are genuinely unresolved,
  US does not go green in this task — that is the honest outcome, and it is better than a silenced gate.

## Step 4 — Verify

- If all 9 resolve to stale-or-known: US exits **0**, and the exit code now means "something a human
  should look at," consistently with CA/UK/AU.
- If any are unresolved: US still exits 1, but now for a **named, listed** reason, not an opaque "9/15."
  Report exactly which targets remain and why.
- CA/UK/AU exit codes and all four reports unchanged (every numeric token identical, timestamps excepted).
- No drift-guard status, band, or `KNOWN_TARGET_DEFECT` entry altered as a side effect.

## Guardrails

- Do not make US exit 0 by weakening the gate without classifying the 9. Green must be earned.
- Do not update a locked target to the current value unless the current value is verified correct (a
  stale target is only stale if the number that replaced it is right).
- No reconciliation math, attribution, bands, or tolerances touched.
- If a target is genuinely unresolved and closing it is non-trivial, **stop and report** — do not
  bundle a real investigation into this task.

## Definition of done

- "Locked targets" mechanism explained; the 15 listed; the 9 failures tabulated (expected/actual/Δ).
- Each of the 9 classified stale / known-defect / unresolved, with evidence.
- Stale targets updated to verified-correct values with a note; known defects given the existing
  expected-status treatment; unresolved ones reported, not silenced.
- US exits 0 **iff** all 9 are legitimately stale-or-known; otherwise exits 1 for a named, listed reason.
- CA/UK/AU and all reported numbers unchanged; no guard/band/registry side effects.
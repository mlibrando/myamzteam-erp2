"use client";

import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
const MARKETPLACES = ["US", "CA", "UK", "AU", "ALL"];
// Native currency per marketplace; only these get a native↔USD toggle (US/ALL are USD-only).
const NATIVE_CCY = { CA: "CAD", UK: "GBP", AU: "AUD" };

// Modernist tokens, reused inline where a semantic class doesn't cover the case.
const MUTED = "color-mix(in srgb, var(--color-text) 55%, transparent)";
const MUTED_STRONG = "color-mix(in srgb, var(--color-text) 65%, transparent)";
const NEG = "var(--color-accent-700)";
const POS = "var(--color-text)";
const DIVIDER = "1px solid var(--color-divider)";

function monthLabel(ym) {
  const [y, m] = ym.split("-");
  return new Date(Number(y), Number(m) - 1, 1).toLocaleString("en-US", { month: "short" });
}

// Currency correctness: the view's own currency + accounting sign (parenthesised
// negatives, like a spreadsheet). Never a GBP figure with a $.
function money(v, currency) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    currencySign: "accounting",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(v);
}

const GearIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="12" cy="12" r="3" />
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
  </svg>
);

export default function Page() {
  const [password, setPassword] = useState(null);
  const [pwInput, setPwInput] = useState("");
  const [marketplace, setMarketplace] = useState("US");
  const [viewCurrency, setViewCurrency] = useState("native"); // "native" | "usd" (CA/UK/AU only)
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(() => new Set());
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [range, setRange] = useState(null); // {start, end} when a custom range is applied
  const [settingsOpen, setSettingsOpen] = useState(false); // salary editor dialog (ALL view)
  const [refreshKey, setRefreshKey] = useState(0); // bump to re-fetch /pnl after a salary edit

  function applyRange(e) {
    e.preventDefault();
    if (startDate && endDate && startDate <= endDate) {
      setRange({ start: startDate, end: endDate });
    }
  }
  function clearRange() {
    setRange(null);
  }

  function toggleRow(name) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }

  useEffect(() => {
    const stored = typeof window !== "undefined" ? sessionStorage.getItem("pnl_pw") : null;
    if (stored) setPassword(stored);
  }, []);

  useEffect(() => {
    if (!password) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    const rangeQs = range ? `&start=${range.start}&end=${range.end}` : "";
    fetch(`${API_BASE}/pnl?marketplace=${marketplace}&currency=${viewCurrency}${rangeQs}`, {
      headers: { "X-Dashboard-Password": password },
    })
      .then(async (res) => {
        if (res.status === 401) {
          sessionStorage.removeItem("pnl_pw");
          if (!cancelled) {
            setPassword(null);
            setData(null);
            setError("Wrong password.");
          }
          return null;
        }
        if (!res.ok) throw new Error(`Server error ${res.status}`);
        return res.json();
      })
      .then((json) => {
        if (json && !cancelled) setData(json);
      })
      .catch((e) => {
        if (!cancelled) setError(e.message || "Request failed");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [password, marketplace, viewCurrency, range, refreshKey]);

  function submitPassword(e) {
    e.preventDefault();
    const pw = pwInput.trim();
    if (!pw) return;
    sessionStorage.setItem("pnl_pw", pw);
    setPassword(pw);
    setPwInput("");
    setError(null);
  }

  // ── Login ──────────────────────────────────────────────────────────────
  if (!password) {
    return (
      <main style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
        <form onSubmit={submitPassword} className="card elev-md" style={{ width: 380, padding: 32, gap: 16 }}>
          <h2 style={{ margin: 0 }}>P&amp;L Dashboard</h2>
          <p style={{ margin: 0, fontSize: 13, color: "color-mix(in srgb, var(--color-text) 60%, transparent)" }}>
            Enter the shared password to continue.
          </p>
          <div className="field">
            <label htmlFor="pw">Password</label>
            <input
              id="pw"
              className="input"
              type="password"
              autoFocus
              value={pwInput}
              onChange={(e) => setPwInput(e.target.value)}
              placeholder="••••••••"
            />
          </div>
          {error && <p style={{ margin: 0, fontSize: 13, color: "var(--color-accent)" }}>{error}</p>}
          <button type="submit" className="btn btn-primary btn-block">Enter</button>
        </form>
      </main>
    );
  }

  const nativeCcy = NATIVE_CCY[marketplace];

  // ── Dashboard ──────────────────────────────────────────────────────────
  return (
    <main style={{ minHeight: "100vh" }}>
      <div className="nav" style={{ padding: "16px 32px" }}>
        <div className="nav-brand">MYAMZTEAM</div>
        <div className="seg">
          {MARKETPLACES.map((mp) => (
            <button
              key={mp}
              type="button"
              className="seg-opt"
              data-active={marketplace === mp}
              onClick={() => setMarketplace(mp)}
            >
              {mp === "ALL" ? "All" : mp}
            </button>
          ))}
        </div>
        {nativeCcy && (
          <div className="seg">
            {[["native", nativeCcy], ["usd", "USD"]].map(([c, label]) => (
              <button
                key={c}
                type="button"
                className="seg-opt"
                data-active={viewCurrency === c}
                onClick={() => setViewCurrency(c)}
              >
                {label}
              </button>
            ))}
          </div>
        )}
        {marketplace === "ALL" && (
          <button
            type="button"
            onClick={() => setSettingsOpen(true)}
            title="Edit salaries"
            aria-label="Edit salaries"
            className="btn btn-icon btn-secondary"
          >
            <GearIcon />
          </button>
        )}
      </div>

      <div style={{ padding: "20px 32px 0" }}>
        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "baseline", justifyContent: "space-between", gap: 12 }}>
          <div>
            <h1 style={{ margin: "0 0 4px" }}>P&amp;L Dashboard</h1>
            <p style={{ margin: 0, fontSize: 13, color: MUTED }}>
              {data?.is_range ? data.range_label : "Settled months (Jan–Jun 2026)"}
              {data && (
                <>
                  {" · "}
                  <strong style={{ color: POS }}>{data.currency}</strong>
                  {data.currency === "USD" && data.native_currency !== "USD" && " (converted at monthly avg rate)"}
                </>
              )}
            </p>
          </div>
          <form onSubmit={applyRange} style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13 }}>
            <span style={{ color: MUTED }}>Date range</span>
            <input
              className="input"
              type="date"
              style={{ width: 150 }}
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
            <span style={{ color: "var(--color-accent)" }}>→</span>
            <input
              className="input"
              type="date"
              style={{ width: 150 }}
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
            <button
              type="submit"
              className="btn btn-secondary"
              disabled={!(startDate && endDate && startDate <= endDate)}
            >
              Apply
            </button>
            {range && (
              <button type="button" className="btn btn-ghost" onClick={clearRange}>
                Clear
              </button>
            )}
          </form>
        </div>
        <hr className="hr" style={{ margin: "16px 0 0" }} />
      </div>

      {loading && (
        <p style={{ padding: "16px 32px", fontSize: 13, color: MUTED }}>Loading…</p>
      )}
      {error && !loading && (
        <p style={{ padding: "16px 32px", fontSize: 13, color: "var(--color-accent)" }}>{error}</p>
      )}

      {data && !loading && (
        <div style={{ padding: "24px 32px 40px", overflowX: "auto" }}>
          <table className="table" style={{ minWidth: 1100 }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left" }}>Line item</th>
                {data.months.map((m) => (
                  <th key={m} style={{ textAlign: "right" }}>
                    {data.is_range ? data.range_label : monthLabel(m)}
                  </th>
                ))}
                {!data.is_range && (
                  <th style={{ textAlign: "right", borderLeft: "2px solid var(--color-divider)" }}>Total</th>
                )}
              </tr>
            </thead>
            <tbody>
              {data.rows.flatMap((row) => {
                const isNet = row.net === true;
                const isRate = row.rate === true;
                const hasChildren = Array.isArray(row.children) && row.children.length > 0;
                const isOpen = expanded.has(row.name);
                const fmt = (v) => (isRate ? v.toFixed(4) : money(v, data.currency));
                const valColor = (v) => (isRate ? MUTED : v < 0 ? NEG : POS);

                const nameCell = isNet ? (
                  <span style={{ fontFamily: "var(--font-heading)", fontWeight: 800 }}>{row.name}</span>
                ) : hasChildren ? (
                  <button
                    type="button"
                    onClick={() => toggleRow(row.name)}
                    aria-expanded={isOpen}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 8,
                      background: "transparent",
                      border: 0,
                      padding: 0,
                      cursor: "pointer",
                      color: "inherit",
                      font: "inherit",
                    }}
                  >
                    <span style={{ fontSize: 10, color: "var(--color-accent)", width: 10, display: "inline-block" }}>
                      {isOpen ? "▾" : "▸"}
                    </span>
                    <span style={{ fontFamily: "var(--font-heading)", fontWeight: 400 }}>{row.name}</span>
                  </button>
                ) : (
                  <span style={{ fontFamily: "var(--font-heading)", fontWeight: 400, color: isRate ? MUTED : POS }}>
                    {row.name}
                  </span>
                );

                const parent = (
                  <tr key={row.name} style={{ borderTop: isNet ? "2px solid var(--color-divider)" : DIVIDER }}>
                    <td style={{ textAlign: "left", whiteSpace: "nowrap" }}>{nameCell}</td>
                    {row.values.map((v, i) => (
                      <td
                        key={i}
                        style={{
                          textAlign: "right",
                          fontVariantNumeric: "tabular-nums",
                          fontWeight: isNet ? 800 : 400,
                          color: valColor(v),
                        }}
                      >
                        {fmt(v)}
                      </td>
                    ))}
                    {!data.is_range && (
                      <td
                        style={{
                          textAlign: "right",
                          fontVariantNumeric: "tabular-nums",
                          fontWeight: 800,
                          color: valColor(row.total),
                          borderLeft: "2px solid var(--color-divider)",
                        }}
                      >
                        {fmt(row.total)}
                        {row.avg && (
                          <span
                            title="Average (per-day figure, not a sum)"
                            style={{
                              marginLeft: 4,
                              fontSize: 10,
                              fontWeight: 400,
                              textTransform: "uppercase",
                              letterSpacing: "0.04em",
                              color: MUTED,
                            }}
                          >
                            avg
                          </span>
                        )}
                      </td>
                    )}
                  </tr>
                );
                if (!hasChildren || !isOpen) return [parent];

                const childRows = row.children.map((child) => (
                  <tr key={`${row.name}::${child.name}`} style={{ borderTop: DIVIDER }}>
                    <td style={{ textAlign: "left", paddingLeft: 34, whiteSpace: "nowrap", color: MUTED_STRONG }}>
                      <span style={{ display: "inline-flex", alignItems: "flex-start", gap: 4 }}>
                        {child.name}
                        {child.hint && (
                          <span className="hint">
                            <span
                              role="img"
                              aria-label={child.hint}
                              tabIndex={0}
                              className="hint-mark"
                            >
                              &#9432;
                            </span>
                            <span role="tooltip" className="hint-tip">
                              {child.hint}
                            </span>
                          </span>
                        )}
                      </span>
                    </td>
                    {child.values.map((v, i) => (
                      <td
                        key={i}
                        style={{
                          textAlign: "right",
                          fontVariantNumeric: "tabular-nums",
                          color: v < 0 ? NEG : MUTED_STRONG,
                        }}
                      >
                        {money(v, data.currency)}
                      </td>
                    ))}
                    {!data.is_range && (
                      <td
                        style={{
                          textAlign: "right",
                          fontVariantNumeric: "tabular-nums",
                          borderLeft: "2px solid var(--color-divider)",
                          color: child.total < 0 ? NEG : MUTED_STRONG,
                        }}
                      >
                        {money(child.total, data.currency)}
                      </td>
                    )}
                  </tr>
                ));
                return [parent, ...childRows];
              })}
            </tbody>
          </table>
        </div>
      )}

      {settingsOpen && (
        <SalaryDialog
          password={password}
          onClose={() => setSettingsOpen(false)}
          onSaved={() => setRefreshKey((k) => k + 1)}
        />
      )}
    </main>
  );
}

// Company-wide daily salaries (USD) editor for the ALL view. Reads GET /salaries, upserts
// changed months via PUT /salaries, and DELETEs an override to revert to the code default.
function SalaryDialog({ password, onClose, onSaved }) {
  const [rows, setRows] = useState(null); // [{year_month, daily_amount, is_override}]
  const [drafts, setDrafts] = useState({}); // { ym: "887" }
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(false);

  const auth = { "X-Dashboard-Password": password };

  function hydrate(months) {
    setRows(months);
    setDrafts(Object.fromEntries(months.map((m) => [m.year_month, String(m.daily_amount)])));
  }

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE}/salaries`, { headers: auth })
      .then((r) => {
        if (!r.ok) throw new Error(`Server error ${r.status}`);
        return r.json();
      })
      .then((j) => !cancelled && hydrate(j.months))
      .catch((e) => !cancelled && setErr(e.message || "Failed to load salaries"));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [password]);

  async function save() {
    if (!rows) return;
    setBusy(true);
    setErr(null);
    try {
      for (const m of rows) {
        const raw = drafts[m.year_month];
        const val = Number(raw);
        if (raw === "" || Number.isNaN(val) || val < 0) {
          throw new Error(`Enter a valid amount for ${m.year_month}`);
        }
        if (val !== Number(m.daily_amount)) {
          const res = await fetch(`${API_BASE}/salaries`, {
            method: "PUT",
            headers: { ...auth, "Content-Type": "application/json" },
            body: JSON.stringify({ year_month: m.year_month, daily_amount: val }),
          });
          if (!res.ok) throw new Error(`Save failed for ${m.year_month}`);
        }
      }
      onSaved();
      onClose();
    } catch (e) {
      setErr(e.message || "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function resetMonth(ym) {
    setBusy(true);
    setErr(null);
    try {
      const res = await fetch(`${API_BASE}/salaries/${ym}`, { method: "DELETE", headers: auth });
      if (!res.ok) throw new Error(`Reset failed for ${ym}`);
      const r2 = await fetch(`${API_BASE}/salaries`, { headers: auth });
      hydrate((await r2.json()).months);
    } catch (e) {
      setErr(e.message || "Reset failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="dialog-backdrop" onClick={onClose}>
      <div className="dialog" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div className="dialog-title">Salaries (daily, USD)</div>
          <button type="button" onClick={onClose} aria-label="Close" className="btn btn-icon btn-ghost">
            ✕
          </button>
        </div>
        <p className="dialog-body" style={{ margin: 0 }}>
          Company-wide daily salary per month. Applied to the contribution rows on the All view.
        </p>

        {!rows && !err && <p style={{ margin: 0, fontSize: 13, color: MUTED }}>Loading…</p>}
        {err && <p style={{ margin: 0, fontSize: 13, color: "var(--color-accent)" }}>{err}</p>}

        {rows && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {rows.map((m) => (
              <div key={m.year_month} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <label htmlFor={`sal-${m.year_month}`} style={{ width: 100, fontSize: 13, color: MUTED_STRONG }}>
                  {monthLabel(m.year_month)} {m.year_month.slice(0, 4)}
                </label>
                <input
                  id={`sal-${m.year_month}`}
                  className="input"
                  type="number"
                  min="0"
                  step="0.01"
                  style={{ width: 140 }}
                  value={drafts[m.year_month] ?? ""}
                  onChange={(e) => setDrafts((d) => ({ ...d, [m.year_month]: e.target.value }))}
                />
                {m.is_override ? (
                  <button
                    type="button"
                    onClick={() => resetMonth(m.year_month)}
                    disabled={busy}
                    className="btn btn-ghost"
                    style={{ fontSize: 11, paddingInline: 0 }}
                  >
                    reset
                  </button>
                ) : (
                  <span style={{ fontSize: 11, color: "color-mix(in srgb, var(--color-text) 45%, transparent)" }}>
                    default
                  </span>
                )}
              </div>
            ))}
          </div>
        )}

        <div className="dialog-actions">
          <button type="button" onClick={onClose} className="btn btn-secondary">
            Cancel
          </button>
          <button type="button" onClick={save} disabled={busy || !rows} className="btn btn-primary">
            {busy ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}

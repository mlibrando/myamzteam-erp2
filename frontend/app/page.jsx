"use client";

import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
const MARKETPLACES = ["US", "CA", "UK", "AU", "ALL"];
// Native currency per marketplace; only these get a native↔USD toggle (US/ALL are USD-only).
const NATIVE_CCY = { CA: "CAD", UK: "GBP", AU: "AUD" };

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

  if (!password) {
    return (
      <main className="min-h-screen flex items-center justify-center p-6">
        <form
          onSubmit={submitPassword}
          className="w-full max-w-sm bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4"
        >
          <h1 className="text-lg font-semibold">P&amp;L Dashboard</h1>
          <p className="text-sm text-slate-500">Enter the shared password to continue.</p>
          <input
            type="password"
            autoFocus
            value={pwInput}
            onChange={(e) => setPwInput(e.target.value)}
            placeholder="Password"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            className="w-full rounded-lg bg-slate-900 text-white text-sm font-medium py-2 hover:bg-slate-700"
          >
            Enter
          </button>
        </form>
      </main>
    );
  }

  return (
    <main className="min-h-screen p-4 sm:p-8">
      <div className="max-w-6xl mx-auto space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold">P&amp;L Dashboard</h1>
            <p className="text-sm text-slate-500">
              {data?.is_range ? data.range_label : "Settled months (Jan–Jun 2026)"}{" "}
              {data && (
                <>
                  · <span className="font-medium">{data.currency}</span>
                  {data.currency === "USD" &&
                    data.native_currency !== "USD" &&
                    " (converted at monthly avg rate)"}
                </>
              )}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <nav className="inline-flex rounded-lg border border-slate-300 overflow-hidden">
              {MARKETPLACES.map((mp) => (
                <button
                  key={mp}
                  onClick={() => setMarketplace(mp)}
                  className={
                    "px-4 py-2 text-sm font-medium border-l first:border-l-0 border-slate-300 " +
                    (marketplace === mp
                      ? "bg-slate-900 text-white"
                      : "bg-white text-slate-700 hover:bg-slate-100")
                  }
                >
                  {mp === "ALL" ? "All" : mp}
                </button>
              ))}
            </nav>
            {NATIVE_CCY[marketplace] && (
              <nav className="inline-flex rounded-lg border border-slate-300 overflow-hidden">
                {[["native", NATIVE_CCY[marketplace]], ["usd", "USD"]].map(([c, label]) => (
                  <button
                    key={c}
                    onClick={() => setViewCurrency(c)}
                    className={
                      "px-4 py-2 text-sm font-medium border-l first:border-l-0 border-slate-300 " +
                      (viewCurrency === c
                        ? "bg-slate-900 text-white"
                        : "bg-white text-slate-700 hover:bg-slate-100")
                    }
                  >
                    {label}
                  </button>
                ))}
              </nav>
            )}
            {marketplace === "ALL" && (
              <button
                type="button"
                onClick={() => setSettingsOpen(true)}
                title="Edit salaries"
                aria-label="Edit salaries"
                className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-600 hover:bg-slate-100"
              >
                <span aria-hidden="true">⚙</span>
              </button>
            )}
          </div>
        </div>

        <form onSubmit={applyRange} className="flex flex-wrap items-center gap-2 text-sm">
          <span className="text-slate-500">Date range</span>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="rounded-lg border border-slate-300 px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-slate-400"
          />
          <span className="text-slate-400">→</span>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="rounded-lg border border-slate-300 px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-slate-400"
          />
          <button
            type="submit"
            disabled={!(startDate && endDate && startDate <= endDate)}
            className="rounded-lg bg-slate-900 text-white font-medium px-3 py-1.5 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Apply
          </button>
          {range && (
            <button
              type="button"
              onClick={clearRange}
              className="rounded-lg border border-slate-300 font-medium px-3 py-1.5 text-slate-700 hover:bg-slate-100"
            >
              Clear · back to months
            </button>
          )}
        </form>

        {loading && <p className="text-sm text-slate-500">Loading…</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}

        {data && !loading && (
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-x-auto">
            <table className="w-full text-sm tabular-nums">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500">
                  <th className="text-left font-medium px-4 py-3 sticky left-0 bg-white">Line item</th>
                  {data.months.map((m) => (
                    <th key={m} className="text-right font-medium px-4 py-3 whitespace-nowrap">
                      {data.is_range ? data.range_label : monthLabel(m)}
                    </th>
                  ))}
                  {!data.is_range && (
                    <th className="text-right font-semibold px-4 py-3 whitespace-nowrap border-l border-slate-200">
                      Total
                    </th>
                  )}
                </tr>
              </thead>
              <tbody>
                {data.rows.flatMap((row) => {
                  const isNet = row.net === true;
                  const isRate = row.rate === true;
                  const hasChildren =
                    Array.isArray(row.children) && row.children.length > 0;
                  const isOpen = expanded.has(row.name);
                  const fmt = (v) => (isRate ? v.toFixed(4) : money(v, data.currency));
                  const parent = (
                    <tr
                      key={row.name}
                      className={
                        isNet
                          ? "border-t-2 border-slate-300 font-semibold"
                          : isRate
                          ? "border-t border-slate-200 text-slate-400"
                          : "border-t border-slate-100"
                      }
                    >
                      <td className="text-left px-4 py-2.5 sticky left-0 bg-white whitespace-nowrap">
                        {hasChildren ? (
                          <button
                            type="button"
                            onClick={() => toggleRow(row.name)}
                            aria-expanded={isOpen}
                            className="inline-flex items-center gap-1.5 hover:text-slate-900"
                          >
                            <span className="text-slate-400 text-xs w-3 text-center">
                              {isOpen ? "▾" : "▸"}
                            </span>
                            {row.name}
                          </button>
                        ) : (
                          row.name
                        )}
                      </td>
                      {row.values.map((v, i) => (
                        <td
                          key={i}
                          className={
                            "text-right px-4 py-2.5 whitespace-nowrap " +
                            (isRate
                              ? "text-slate-400"
                              : v < 0
                              ? "text-red-600"
                              : "text-slate-800")
                          }
                        >
                          {fmt(v)}
                        </td>
                      ))}
                      {!data.is_range && (
                        <td
                          className={
                            "text-right px-4 py-2.5 whitespace-nowrap border-l border-slate-200 " +
                            (isRate
                              ? "text-slate-400"
                              : "font-medium " +
                                (row.total < 0 ? "text-red-600" : "text-slate-900"))
                          }
                        >
                          {fmt(row.total)}
                          {row.avg && (
                            <span
                              className="ml-1 align-middle text-[10px] font-normal uppercase tracking-wide text-slate-400"
                              title="Average (per-day figure, not a sum)"
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
                    <tr
                      key={`${row.name}::${child.name}`}
                      className="border-t border-slate-50"
                    >
                      <td className="text-left pl-10 pr-4 py-2 sticky left-0 bg-white whitespace-nowrap text-slate-500">
                        <span className="inline-flex items-start gap-1">
                          {child.name}
                          {child.hint && (
                            <span className="group relative inline-block">
                              <span
                                role="img"
                                aria-label={child.hint}
                                tabIndex={0}
                                className="cursor-help align-super text-[10px] leading-none text-slate-400 hover:text-slate-600 focus:text-slate-600 focus:outline-none"
                              >
                                &#9432;
                              </span>
                              <span
                                role="tooltip"
                                className="pointer-events-none absolute bottom-full left-0 z-20 mb-1 w-60 whitespace-normal rounded-md bg-slate-800 px-2.5 py-1.5 text-xs font-normal leading-snug text-white opacity-0 shadow-lg transition-opacity duration-150 group-hover:opacity-100 group-focus-within:opacity-100"
                              >
                                {child.hint}
                              </span>
                            </span>
                          )}
                        </span>
                      </td>
                      {child.values.map((v, i) => (
                        <td
                          key={i}
                          className={
                            "text-right px-4 py-2 whitespace-nowrap " +
                            (v < 0 ? "text-red-500" : "text-slate-500")
                          }
                        >
                          {money(v, data.currency)}
                        </td>
                      ))}
                      {!data.is_range && (
                        <td
                          className={
                            "text-right px-4 py-2 whitespace-nowrap border-l border-slate-200 " +
                            (child.total < 0 ? "text-red-500" : "text-slate-500")
                          }
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

      </div>
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
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-1 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Salaries (daily, USD)</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="text-slate-400 hover:text-slate-700"
          >
            ✕
          </button>
        </div>
        <p className="mb-4 text-sm text-slate-500">
          Company-wide daily salary per month. Applied to the contribution rows on the All view.
        </p>

        {!rows && !err && <p className="text-sm text-slate-500">Loading…</p>}
        {err && <p className="mb-3 text-sm text-red-600">{err}</p>}

        {rows && (
          <div className="space-y-2">
            {rows.map((m) => (
              <div key={m.year_month} className="flex items-center gap-3">
                <label className="w-28 text-sm text-slate-600" htmlFor={`sal-${m.year_month}`}>
                  {monthLabel(m.year_month)} {m.year_month.slice(0, 4)}
                </label>
                <input
                  id={`sal-${m.year_month}`}
                  type="number"
                  min="0"
                  step="0.01"
                  value={drafts[m.year_month] ?? ""}
                  onChange={(e) =>
                    setDrafts((d) => ({ ...d, [m.year_month]: e.target.value }))
                  }
                  className="w-32 rounded-lg border border-slate-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
                />
                {m.is_override ? (
                  <button
                    type="button"
                    onClick={() => resetMonth(m.year_month)}
                    disabled={busy}
                    className="text-xs text-slate-500 underline hover:text-slate-800 disabled:opacity-40"
                  >
                    reset
                  </button>
                ) : (
                  <span className="text-xs text-slate-400">default</span>
                )}
              </div>
            ))}
          </div>
        )}

        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={save}
            disabled={busy || !rows}
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-40"
          >
            {busy ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}

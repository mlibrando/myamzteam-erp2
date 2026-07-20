"use client";

import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
const MARKETPLACES = ["US", "CA", "UK", "AU", "ALL"];

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
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const stored = typeof window !== "undefined" ? sessionStorage.getItem("pnl_pw") : null;
    if (stored) setPassword(stored);
  }, []);

  useEffect(() => {
    if (!password) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetch(`${API_BASE}/pnl?marketplace=${marketplace}`, {
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
  }, [password, marketplace]);

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
              Settled months (Jan–Jun 2026){" "}
              {data && (
                <>
                  · <span className="font-medium">{data.currency}</span>
                  {marketplace === "ALL" && " (converted at book rates)"}
                </>
              )}
            </p>
          </div>
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
        </div>

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
                      {monthLabel(m)}
                    </th>
                  ))}
                  <th className="text-right font-semibold px-4 py-3 whitespace-nowrap border-l border-slate-200">
                    Total
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.rows.map((row) => {
                  const isNet = row.name === "Profit";
                  return (
                    <tr
                      key={row.name}
                      className={
                        isNet
                          ? "border-t-2 border-slate-300 font-semibold"
                          : "border-t border-slate-100"
                      }
                    >
                      <td className="text-left px-4 py-2.5 sticky left-0 bg-white whitespace-nowrap">
                        {row.name}
                      </td>
                      {row.values.map((v, i) => (
                        <td
                          key={i}
                          className={
                            "text-right px-4 py-2.5 whitespace-nowrap " +
                            (v < 0 ? "text-red-600" : "text-slate-800")
                          }
                        >
                          {money(v, data.currency)}
                        </td>
                      ))}
                      <td
                        className={
                          "text-right px-4 py-2.5 whitespace-nowrap border-l border-slate-200 font-medium " +
                          (row.total < 0 ? "text-red-600" : "text-slate-900")
                        }
                      >
                        {money(row.total, data.currency)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

      </div>
    </main>
  );
}

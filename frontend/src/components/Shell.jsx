/**
 * PAIR C owns this file. Ships in Phase 0, before the build clock starts.
 * Nav labels are the product story: PS-mandated feature, then our layer under it.
 */
import { NavLink } from "react-router-dom";

const NAV = [
  { to: "/recommend", label: "Scheme Recommender", owner: "A" },
  { to: "/truth", label: "Scheme Truth Layer", owner: "A" },
  { to: "/calculator", label: "Financial Calculator", owner: "B" },
  { to: "/sanction-ready", label: "Sanction-Ready", owner: "B" },
  { to: "/locator", label: "Partner Locator", owner: "C" },
  { to: "/ledger", label: "Transparency Ledger", owner: "C" },
];

export default function Shell({ children }) {
  return (
    <div className="min-h-screen bg-stone-50 text-stone-900">
      <header className="border-b bg-white">
        <div className="mx-auto max-w-6xl px-4 py-3">
          <h1 className="text-lg font-semibold">PS 26092 — NSFDC Application Assistant</h1>
          <nav className="mt-3 flex flex-wrap gap-1">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                className={({ isActive }) =>
                  `rounded px-3 py-1.5 text-sm ${
                    isActive ? "bg-stone-900 text-white" : "text-stone-600 hover:bg-stone-100"
                  }`
                }
              >
                {n.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
    </div>
  );
}

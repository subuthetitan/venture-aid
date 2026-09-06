/**
 * ALL SIX ROUTES REGISTERED ON DAY ZERO.
 *
 * Same reasoning as backend/app/main.py: route registration is a guaranteed
 * three-way merge conflict. Register everything up front, then nobody touches
 * this file during the build. Each pair only edits their own files in pages/.
 *
 * Side benefit: from hour zero you have a clickable six-screen product to
 * demo, even when the screens are still placeholders.
 */
import { Navigate, Route, Routes } from "react-router-dom";

import Shell from "./components/Shell";
import Calculator from "./pages/Calculator";     // Pair B
import Ledger from "./pages/Ledger";             // Pair C
import Locator from "./pages/Locator";           // Pair C
import Recommender from "./pages/Recommender";   // Pair A
import SanctionReady from "./pages/SanctionReady"; // Pair B
import TruthLayer from "./pages/TruthLayer";     // Pair A

export default function App() {
  return (
    <Shell>
      <Routes>
        <Route path="/" element={<Navigate to="/recommend" replace />} />
        <Route path="/recommend" element={<Recommender />} />
        <Route path="/truth" element={<TruthLayer />} />
        <Route path="/calculator" element={<Calculator />} />
        <Route path="/sanction-ready" element={<SanctionReady />} />
        <Route path="/locator" element={<Locator />} />
        <Route path="/ledger" element={<Ledger />} />
      </Routes>
    </Shell>
  );
}

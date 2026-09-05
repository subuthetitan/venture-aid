import { useEffect, useState } from "react";
import DistrictMap from "../components/DistrictMap";
import { api } from "../lib/api";
import { loadDistricts } from "../lib/districts";

const LAYERS = [
  { id: "channels", label: "Channels" },
  { id: "reachability", label: "Reachability" },
  { id: "pendency", label: "Pendency" },
];

export default function Locator() {
  const [layer, setLayer] = useState("channels");
  const [districts, setDistricts] = useState(null);
  const [reachability, setReachability] = useState([]);
  const [ledger, setLedger] = useState([]);
  const [selected, setSelected] = useState(null);
  const [channels, setChannels] = useState([]);
  const [routeGeometry, setRouteGeometry] = useState(null);
  const [routeNote, setRouteNote] = useState(null);

  useEffect(() => {
    loadDistricts().then(setDistricts).catch(() => setDistricts(null));
    api.reachability().then(setReachability).catch(() => setReachability([]));
    api.ledger().then((r) => setLedger(r.cells ?? [])).catch(() => setLedger([]));
  }, []);

  async function handleDistrictClick(props) {
    setRouteGeometry(null);
    setRouteNote(null);

    const key = Object.keys(props).find((k) => k.toLowerCase() === "censuscode");
    const code = String(props[key]);
    const cell = reachability.find((d) => String(d.district_code) === code);

    if (!cell) {
      setSelected({ unchecked: true, code, name: props.DISTRICT, state: props.ST_NM });
      setChannels([]);
      return;
    }

    const list = await api.channels(code).catch(() => []);
    setChannels(list);
    setSelected({
      code,
      name: districts?.districtName(code) ?? props.DISTRICT,
      state: districts?.stateName(cell.state_code) ?? props.ST_NM,
      cell,
    });
  }

  function handleRoute(channelId) {
    if (!navigator.geolocation) {
      setRouteNote("Location unavailable in this browser.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const r = await api.route({
            from_lat: pos.coords.latitude,
            from_lon: pos.coords.longitude,
            to_channel_id: channelId,
          });
          setRouteGeometry(r.geometry);
          setRouteNote(
            r.provider === "fixture"
              ? "Live routing unavailable - straight-line distance only, " + r.distance_km + " km."
              : r.distance_km + " km, about " + Math.round(r.duration_min) + " min."
          );
        } catch {
          setRouteNote("Could not compute a route.");
        }
      },
      () => setRouteNote("Location permission denied - cannot compute a route.")
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <section className="lg:col-span-2">
        <div className="flex gap-2 mb-3">
          {LAYERS.map((l) => (
            <button
              key={l.id}
              onClick={() => setLayer(l.id)}
              className={
                "px-3 py-1.5 text-sm rounded border " +
                (layer === l.id
                  ? "bg-stone-900 text-white border-stone-900"
                  : "border-stone-300 text-stone-600 hover:bg-stone-100")
              }
            >
              {l.label}
            </button>
          ))}
        </div>

        <DistrictMap
          layer={layer}
          reachability={reachability}
          ledger={ledger}
          channels={channels}
          routeGeometry={routeGeometry}
          onDistrictClick={handleDistrictClick}
        />

        <Legend layer={layer} />
      </section>

      <aside className="border border-stone-200 rounded-lg p-4 bg-white h-fit">
        {!selected && (
          <p className="text-sm text-stone-500">Select a district on the map.</p>
        )}

        {selected?.unchecked && (
          <>
            <h3 className="font-medium">{selected.name}</h3>
            <p className="text-xs text-stone-500">{selected.state}</p>
            <p className="mt-3 text-sm text-stone-600">
              Not in our checked set. We show status only for districts we have
              actually verified.
            </p>
          </>
        )}

        {selected && !selected.unchecked && (
          <>
            <h3 className="font-medium">{selected.name}</h3>
            <p className="text-xs text-stone-500">{selected.state}</p>

            {!selected.cell.has_sca && (
              <div className="mt-3 p-3 rounded bg-stone-900 text-stone-100 text-sm">
                <strong>No channel available.</strong>
                <p className="mt-1 text-xs text-stone-300">{selected.cell.note}</p>
              </div>
            )}

            {selected.cell.has_sca && channels.length === 0 && (
              <p className="mt-3 text-sm text-stone-600">{selected.cell.note}</p>
            )}

            {channels.length > 0 && (
              <ul className="mt-4 space-y-3">
                {channels.map((c) => (
                  <li key={c.id} className="border-b border-stone-200 pb-3">
                    <p className="text-sm font-medium">{c.name}</p>
                    <p className="text-xs text-stone-500 uppercase">{c.kind}</p>
                    {c.address && <p className="text-xs mt-1">{c.address}</p>}
                    <p className="text-xs">
                      {c.phone ?? (
                        <span className="italic text-stone-400">
                          Contact number not published
                        </span>
                      )}
                    </p>
                    {c.lat != null && (
                      <button
                        onClick={() => handleRoute(c.id)}
                        className="mt-2 text-xs text-teal-800 underline"
                      >
                        Get directions
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}

            {routeNote && <p className="mt-3 text-xs text-amber-700">{routeNote}</p>}
          </>
        )}
      </aside>
    </div>
  );
}

function Legend({ layer }) {
  if (layer === "reachability") {
    return (
      <div className="mt-3 flex flex-wrap gap-4 text-xs text-stone-600">
        <Swatch color="#15803d" label="Channel exists" />
        <Swatch color="#292524" label="No agency - nowhere to apply" />
        <Swatch color="#d6d3d1" label="Not checked" />
      </div>
    );
  }
  if (layer === "pendency") {
    return (
      <div className="mt-3">
        <div className="flex flex-wrap gap-4 text-xs text-stone-600">
          <Swatch color="#15803d" label="Up to 95 days" />
          <Swatch color="#b45309" label="95-105 days" />
          <Swatch color="#b91c1c" label="Over 105 days" />
          <Swatch color="#d6d3d1" label="Suppressed or no data" />
        </div>
        <p className="mt-2 text-xs font-medium text-amber-700">
          Prototype data - synthetic.
        </p>
      </div>
    );
  }
  return null;
}

function Swatch({ color, label }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className="w-3 h-3 rounded-sm" style={{ background: color }} />
      {label}
    </span>
  );
}
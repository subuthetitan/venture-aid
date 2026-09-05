import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

const INDIA_CENTER = [80.0, 22.0];
const INITIAL_ZOOM = 3.6;

// Joins on censuscode from the DataMeet Census 2011 boundaries.
const JOIN_KEY = "censuscode";

const COLOR = {
  base: "#e7e5e4",
  reachable: "#15803d",
  noSca: "#292524",
  unchecked: "#d6d3d1",
  fast: "#15803d",
  medium: "#b45309",
  slow: "#b91c1c",
};

export default function DistrictMap({
  layer = "channels",
  reachability = [],
  ledger = [],
  channels = [],
  routeGeometry = null,
  onDistrictClick,
}) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const clickHandler = useRef(onDistrictClick);
  const [ready, setReady] = useState(false);
  const [loadError, setLoadError] = useState(null);

  clickHandler.current = onDistrictClick;

  useEffect(() => {
    if (mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: {
        version: 8,
        sources: {},
        layers: [
          { id: "bg", type: "background", paint: { "background-color": "#f5f5f4" } },
        ],
      },
      center: INDIA_CENTER,
      zoom: INITIAL_ZOOM,
      attributionControl: false,
    });
    mapRef.current = map;

    map.addControl(new maplibregl.NavigationControl(), "top-right");
    map.addControl(
      new maplibregl.AttributionControl({
        compact: true,
        customAttribution: "Boundaries: DataMeet (CC BY 4.0), Census 2011",
      })
    );

    map.on("load", async () => {
      try {
        const res = await fetch("/geo/districts.geojson");
        if (!res.ok) throw new Error(`GeoJSON ${res.status}`);
        const geo = await res.json();

        map.addSource("districts", { type: "geojson", data: geo });

        map.addLayer({
          id: "district-fill",
          type: "fill",
          source: "districts",
          paint: { "fill-color": COLOR.base, "fill-opacity": 0.9 },
        });

        map.addLayer({
          id: "district-line",
          type: "line",
          source: "districts",
          paint: { "line-color": "#a8a29e", "line-width": 0.4 },
        });

        map.addSource("channels", {
          type: "geojson",
          data: { type: "FeatureCollection", features: [] },
        });
        map.addLayer({
          id: "channel-points",
          type: "circle",
          source: "channels",
          paint: {
            "circle-radius": 6,
            "circle-color": "#1e5f74",
            "circle-stroke-width": 2,
            "circle-stroke-color": "#ffffff",
          },
        });

        map.addSource("route", {
          type: "geojson",
          data: { type: "FeatureCollection", features: [] },
        });
        map.addLayer({
          id: "route-line",
          type: "line",
          source: "route",
          paint: {
            "line-color": "#1e5f74",
            "line-width": 3,
            "line-dasharray": [2, 1],
          },
        });

        map.on("click", "district-fill", (e) => {
          const props = e.features?.[0]?.properties;
          if (props) clickHandler.current?.(props);
        });
        map.on("mouseenter", "district-fill", () => {
          map.getCanvas().style.cursor = "pointer";
        });
        map.on("mouseleave", "district-fill", () => {
          map.getCanvas().style.cursor = "";
        });

        setReady(true);
      } catch (err) {
        setLoadError(err.message);
      }
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!ready || !mapRef.current) return;
    mapRef.current.setPaintProperty(
      "district-fill",
      "fill-color",
      colorExpression(layer, reachability, ledger)
    );
  }, [ready, layer, reachability, ledger]);

  useEffect(() => {
    if (!ready || !mapRef.current) return;
    mapRef.current.getSource("channels")?.setData({
      type: "FeatureCollection",
      features: channels
        .filter((c) => c.lat != null && c.lon != null)
        .map((c) => ({
          type: "Feature",
          geometry: { type: "Point", coordinates: [Number(c.lon), Number(c.lat)] },
          properties: { id: c.id, name: c.name },
        })),
    });
  }, [ready, channels]);

  useEffect(() => {
    if (!ready || !mapRef.current) return;
    mapRef.current.getSource("route")?.setData(
      routeGeometry
        ? { type: "Feature", geometry: routeGeometry, properties: {} }
        : { type: "FeatureCollection", features: [] }
    );
  }, [ready, routeGeometry]);

  return (
    <div className="relative">
      <div
        ref={containerRef}
        className="w-full h-[520px] rounded-lg border border-stone-200"
      />
      {loadError && (
        <div className="absolute inset-0 grid place-items-center bg-stone-50/90 rounded-lg">
          <p className="text-sm text-red-700">Map data failed to load: {loadError}</p>
        </div>
      )}
    </div>
  );
}

function colorExpression(layer, reachability, ledger) {
  if (layer === "reachability" && reachability.length) {
    const expr = ["match", ["to-string", ["get", JOIN_KEY]]];
    for (const d of reachability) {
      expr.push(String(d.district_code));
      expr.push(
        !d.has_sca ? COLOR.noSca
          : d.channel_count > 0 ? COLOR.reachable
          : COLOR.unchecked
      );
    }
    expr.push(COLOR.unchecked);
    return expr;
  }

  if (layer === "pendency" && ledger.length) {
    const expr = ["match", ["to-string", ["get", JOIN_KEY]]];
    for (const d of ledger) {
      const v = d.suppressed ? null : d.median_days_to_sanction;
      expr.push(String(d.district_code));
      expr.push(
        v == null ? COLOR.unchecked
          : v > 105 ? COLOR.slow
          : v > 95 ? COLOR.medium
          : COLOR.fast
      );
    }
    expr.push(COLOR.unchecked);
    return expr;
  }

  return COLOR.base;
}
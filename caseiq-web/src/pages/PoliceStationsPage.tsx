import L from "leaflet";
import "leaflet/dist/leaflet.css";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";
import { useEffect, useRef, useState } from "react";
import styles from "./PoliceStationsPage.module.css";

// Vite bundles Leaflet's default marker images under a hashed path Leaflet's
// own icon resolution can't find at runtime -- the standard fix is pointing
// it at the bundled asset URLs directly.
delete (L.Icon.Default.prototype as unknown as { _getIconUrl?: unknown })._getIconUrl;
L.Icon.Default.mergeOptions({ iconRetinaUrl: markerIcon2x, iconUrl: markerIcon, shadowUrl: markerShadow });

// Required fallback path, not an edge case: shown whenever geolocation is
// denied, unsupported, or times out.
const MUMBAI_CENTER: [number, number] = [19.076, 72.8777];
const SEARCH_RADIUS_M = 5000;
const MAX_RESULTS = 20; // capped, not unbounded -- see fetchOverpass

// Public, unmetered mirrors -- tried in order, first success wins. No API
// key exists for any of these; this is the whole reason they're flaky under
// load, not a configuration problem on our end.
const OVERPASS_ENDPOINTS = [
  "https://overpass-api.de/api/interpreter",
  "https://lz4.overpass-api.de/api/interpreter",
  "https://overpass.kumi.systems/api/interpreter",
];

async function fetchOverpass(query: string): Promise<{ elements: unknown[] }> {
  let lastError: unknown;
  for (const endpoint of OVERPASS_ENDPOINTS) {
    try {
      // A per-mirror timeout, not just a per-query one in the Overpass query
      // language itself -- that server-side [timeout:15] only bounds how
      // long Overpass spends computing an answer, not how long a slow or
      // hanging mirror leaves the browser's fetch() pending. Without this,
      // one bad mirror can stall the whole fallback chain far longer than
      // the "try the next one" design intends.
      const res = await fetch(endpoint, {
        method: "POST",
        body: query,
        signal: AbortSignal.timeout(8000),
      });
      if (!res.ok) throw new Error(`${endpoint} returned ${res.status}`);
      return await res.json();
    } catch (err) {
      lastError = err;
    }
  }
  throw lastError ?? new Error("all Overpass endpoints failed");
}

type Station = {
  id: number;
  name: string;
  lat: number;
  lon: number;
  address: string;
  distanceKm: number;
};

function haversineKm(a: [number, number], b: [number, number]): number {
  const R = 6371;
  const dLat = ((b[0] - a[0]) * Math.PI) / 180;
  const dLon = ((b[1] - a[1]) * Math.PI) / 180;
  const lat1 = (a[0] * Math.PI) / 180;
  const lat2 = (b[0] * Math.PI) / 180;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(h), Math.sqrt(1 - h));
}

function formatAddress(tags: Record<string, string>): string {
  const parts = [tags["addr:housenumber"], tags["addr:street"], tags["addr:suburb"], tags["addr:city"]]
    .filter(Boolean);
  return parts.length > 0 ? parts.join(", ") : "Address not available on OpenStreetMap";
}

/**
 * OpenStreetMap + Overpass + Leaflet, deliberately not Google Maps: the
 * Google Maps JS API requires a billing account with a card even on the free
 * tier, and without one shows a "for development purposes only" watermark
 * that makes the map unusable for a demo. OSM needs neither a key nor a card.
 */
export function PoliceStationsPage() {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);

  const [center, setCenter] = useState<[number, number] | null>(null);
  const [geoStatus, setGeoStatus] = useState<"locating" | "granted" | "denied">("locating");
  const [cityQuery, setCityQuery] = useState("");
  const [cityError, setCityError] = useState<string | null>(null);
  const [stations, setStations] = useState<Station[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Geolocation on mount -- falls back to Mumbai on denial, timeout, or an
  // unsupported browser. Required path, not an edge case.
  useEffect(() => {
    if (!navigator.geolocation) {
      setGeoStatus("denied");
      setCenter(MUMBAI_CENTER);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setCenter([pos.coords.latitude, pos.coords.longitude]);
        setGeoStatus("granted");
      },
      () => {
        setGeoStatus("denied");
        setCenter(MUMBAI_CENTER);
      },
      { timeout: 8000 },
    );
  }, []);

  // Create the map once, when a center first becomes known.
  useEffect(() => {
    if (!center || !mapContainerRef.current || mapRef.current) return;
    const map = L.map(mapContainerRef.current).setView(center, 14);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map);
    markersLayerRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;
  }, [center]);

  // Re-centre on later changes (a city search after the map already exists).
  useEffect(() => {
    if (mapRef.current && center) mapRef.current.setView(center, 14);
  }, [center]);

  // Overpass query, re-run whenever the centre changes.
  useEffect(() => {
    if (!center) return;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        // The public Overpass instance is a shared, unmetered community
        // resource -- confirmed directly (plain curl, no browser involved)
        // that its main endpoint 504s under load ("server too busy") even
        // for this exact query. A capped result count and a mirror fallback
        // measurably improved success while testing this (2026-08-31) --
        // not a fix for Overpass's own capacity, just resilience against it.
        const query = `[out:json][timeout:15];node["amenity"="police"](around:${SEARCH_RADIUS_M},${center[0]},${center[1]});out body ${MAX_RESULTS};`;
        const json = await fetchOverpass(query);
        type OverpassEl = { id: number; lat: number; lon: number; tags?: Record<string, string> };
        const list: Station[] = (json.elements as OverpassEl[])
          .filter((el) => el.lat != null && el.lon != null)
          .map((el) => ({
            id: el.id,
            name: el.tags?.name || "Police Station",
            lat: el.lat,
            lon: el.lon,
            address: formatAddress(el.tags ?? {}),
            distanceKm: haversineKm(center, [el.lat, el.lon]),
          }))
          .sort((a, b) => a.distanceKm - b.distanceKm);
        setStations(list);

        const layer = markersLayerRef.current;
        if (layer) {
          layer.clearLayers();
          L.marker(center).addTo(layer).bindPopup("You are here");
          for (const s of list) {
            L.marker([s.lat, s.lon]).addTo(layer).bindPopup(`<b>${s.name}</b><br/>${s.address}`);
          }
        }
      } catch {
        setError("Could not reach the police-station data source (Overpass API). Please try again.");
        setStations(null);
      } finally {
        setLoading(false);
      }
    })();
  }, [center]);

  async function handleCitySearch(e: React.FormEvent) {
    e.preventDefault();
    if (!cityQuery.trim()) return;
    setCityError(null);
    try {
      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(cityQuery)}&format=json&limit=1`,
      );
      const results: { lat: string; lon: string }[] = await res.json();
      if (!results.length) {
        setCityError(`No location found for "${cityQuery}".`);
        return;
      }
      setCenter([parseFloat(results[0].lat), parseFloat(results[0].lon)]);
    } catch {
      setCityError("Could not search for that city. Please try again.");
    }
  }

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <p className={styles.eyebrow}>Find help nearby</p>
        <h1 className={styles.title}>Nearest police stations</h1>
        <p className={styles.subtitle}>
          Map data from OpenStreetMap volunteers, not Google — no billing account, no watermark.
        </p>
      </header>

      {geoStatus === "denied" && (
        <>
          <form className={styles.searchForm} onSubmit={handleCitySearch}>
            <input
              className={styles.searchInput}
              placeholder="Search a city (e.g. Pune, Delhi)…"
              value={cityQuery}
              onChange={(e) => setCityQuery(e.target.value)}
            />
            <button className={styles.searchButton} type="submit">
              Search
            </button>
          </form>
          <p className={styles.geoNote}>
            Location access wasn't available — showing Mumbai by default. Search a city above, or
            enable location access and reload.
          </p>
          {cityError && <p className={styles.cityError}>{cityError}</p>}
        </>
      )}

      <div ref={mapContainerRef} className={styles.map} />

      {loading && <p className={styles.loading}>Finding nearby stations…</p>}
      {error && <div className={styles.errorBox}>{error}</div>}

      {!loading && !error && stations && stations.length === 0 && (
        <div className={styles.empty}>
          <p className={styles.emptyTitle}>No police stations found nearby</p>
          <p className={styles.emptyBody}>
            OpenStreetMap has no station tagged within {SEARCH_RADIUS_M / 1000} km of this
            location — coverage varies by area. Try searching a nearby city.
          </p>
        </div>
      )}

      {!loading && stations && stations.length > 0 && (
        <ul className={styles.list}>
          {stations.map((s) => (
            <li key={s.id} className={styles.card}>
              <h3 className={styles.stationName}>{s.name}</h3>
              <p className={styles.address}>{s.address}</p>
              <div className={styles.metaRow}>
                <span className={styles.distance}>{s.distanceKm.toFixed(1)} km away</span>
                <a
                  className={styles.directions}
                  href={`https://www.openstreetmap.org/directions?from=${center?.[0]}%2C${center?.[1]}&to=${s.lat}%2C${s.lon}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  Directions ↗
                </a>
              </div>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}

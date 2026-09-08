import L from "leaflet";
import "leaflet/dist/leaflet.css";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";
import { useEffect, useRef, useState } from "react";
import cachedStations from "../data/police-stations-mmr.json";
import { useAuth } from "../contexts/AuthContext";
import styles from "./PoliceStationsPage.module.css";

// Fetched once, server-side (scripts/fetch-police-stations.mjs), not at
// request time -- police stations don't move, so paying Overpass's live,
// flaky cost on every page load for the region almost every demo query hits
// (Mumbai) is pure downside. Live Overpass (below) is now only reached for
// coordinates outside this cached bounding box.
const CACHE_BBOX = cachedStations.bbox;

function isWithinCachedRegion([lat, lon]: [number, number]): boolean {
  return (
    lat >= CACHE_BBOX.south &&
    lat <= CACHE_BBOX.north &&
    lon >= CACHE_BBOX.west &&
    lon <= CACHE_BBOX.east
  );
}

// Vite bundles Leaflet's default marker images under a hashed path Leaflet's
// own icon resolution can't find at runtime -- the standard fix is pointing
// it at the bundled asset URLs directly.
delete (L.Icon.Default.prototype as unknown as { _getIconUrl?: unknown })._getIconUrl;
L.Icon.Default.mergeOptions({ iconRetinaUrl: markerIcon2x, iconUrl: markerIcon, shadowUrl: markerShadow });

// Required fallback path, not an edge case: shown whenever geolocation is
// denied, unsupported, or times out. VESIT, Chembur (verified via
// Nominatim, 2026-09-02 -- the VES campus's Pharmacy building, the nearest
// named POI OSM has tagged on that same campus block; VESIT itself has no
// separate node) -- this is where the app gets demoed from, so the no-
// permission default should already be right for that, not generic
// Mumbai. Confirmed directly against the cached dataset before changing
// this: nearest cached stations from here are Tilak Nagar (2.2km),
// Chembur (2.3km), and Govandi (2.7km) -- genuinely close, no re-fetch of
// the cached set was needed.
const DEFAULT_CENTER: [number, number] = [19.0460308, 72.8900446];
// FIXED 2026-09-02: this used to be a hard cutoff on the cached path too --
// found via a full grid-scan of the cached bbox (~2km spacing), not
// assumed: 58% of the bbox's claimed area has ZERO cached stations within
// 5km, because the 76 cached stations are geographically denser than the
// bbox they're checked against implies (real station lat/lon range is
// visibly smaller than the bbox, and uneven within it -- an OSM tagging-
// density fact, not something this app controls). Any geolocation landing
// in that 58% correctly used the cache (it's inside the bbox) and then
// correctly computed zero results, because real, present stations farther
// than 5km were being discarded rather than shown. 10km is now only the
// LIVE Overpass query's own server-side search radius -- the cached path
// itself no longer hard-filters by distance at all; see below. FIXED
// 2026-09-02: dropped the on-page note that used to explain this (a
// "cached coverage is thinner here" message) per explicit instruction --
// it narrated an implementation detail; the distance already shown on
// every result card says everything a user actually needs.
const SEARCH_RADIUS_M = 10000;
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
  const { user } = useAuth();
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

  // Geolocation on mount -- falls back to DEFAULT_CENTER on denial, timeout,
  // or an unsupported browser. Required path, not an edge case.
  useEffect(() => {
    if (!navigator.geolocation) {
      setGeoStatus("denied");
      setCenter(DEFAULT_CENTER);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setCenter([pos.coords.latitude, pos.coords.longitude]);
        setGeoStatus("granted");
      },
      () => {
        setGeoStatus("denied");
        setCenter(DEFAULT_CENTER);
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

  // Station lookup, re-run whenever the centre changes. Cached MMR data
  // first (no network at all -- see below for why this is the case the
  // caching exists for); live Overpass only for coordinates outside it.
  useEffect(() => {
    if (!center) return;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        if (isWithinCachedRegion(center)) {
          // FIXED: no distance filter here any more -- see SEARCH_RADIUS_M's
          // comment. The nearest cached station is always more useful than
          // "none found", however far it turns out to be; the UI shows the
          // real distance on every card, and a note appears separately when
          // even the nearest one is far enough that "thin coverage here" is
          // the honest read, rather than silently returning distant results
          // with no context.
          const list: Station[] = cachedStations.stations
            .map((s) => ({ ...s, distanceKm: haversineKm(center, [s.lat, s.lon]) }))
            .sort((a, b) => a.distanceKm - b.distanceKm)
            .slice(0, MAX_RESULTS);
          setStations(list);
          renderMarkers(center, list);
          return;
        }

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
        renderMarkers(center, list);
      } catch {
        setError("Could not reach the police-station data source (Overpass API). Please try again.");
        setStations(null);
      } finally {
        setLoading(false);
      }
    })();

    function renderMarkers(c: [number, number], list: Station[]) {
      const layer = markersLayerRef.current;
      if (!layer) return;
      layer.clearLayers();
      L.marker(c).addTo(layer).bindPopup("You are here");
      for (const s of list) {
        L.marker([s.lat, s.lon]).addTo(layer).bindPopup(`<b>${s.name}</b><br/>${s.address}`);
      }
    }
  }, [center]);

  // Extracted 2026-09-07 (was inline in handleCitySearch) so the saved-
  // state/district autofill below can trigger the exact same lookup a
  // manual search does, rather than duplicating it.
  async function geocodeAndCenter(q: string): Promise<boolean> {
    try {
      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(q)}&format=json&limit=1`,
      );
      const results: { lat: string; lon: string }[] = await res.json();
      if (!results.length) {
        setCityError(`No location found for "${q}".`);
        return false;
      }
      setCenter([parseFloat(results[0].lat), parseFloat(results[0].lon)]);
      return true;
    } catch {
      setCityError("Could not search for that city. Please try again.");
      return false;
    }
  }

  async function handleCitySearch(e: React.FormEvent) {
    e.preventDefault();
    if (!cityQuery.trim()) return;
    setCityError(null);
    await geocodeAndCenter(cityQuery);
  }

  // Added 2026-09-07: a logged-in user's saved district/state (profile
  // page preferences) prefills the city search the moment geolocation is
  // denied, instead of leaving the hardcoded DEFAULT_CENTER (Mumbai/
  // VESIT) as the only fallback. Override, not replacement -- geolocation
  // still wins whenever it's actually granted (real-time, more accurate
  // than a saved region), this only improves the DENIED path, and typing
  // a different city afterward still overrides it for that visit, same
  // as any other search. Runs once per denial (the `ran` ref, not
  // `geoStatus` alone, so it doesn't refire on unrelated re-renders or
  // fight a city search the person already typed themselves).
  const autofillRanRef = useRef(false);
  useEffect(() => {
    if (geoStatus !== "denied" || autofillRanRef.current) return;
    if (!user?.district && !user?.state) return;
    autofillRanRef.current = true;
    const q = [user.district, user.state].filter(Boolean).join(", ");
    setCityQuery(q);
    void geocodeAndCenter(q);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [geoStatus, user?.district, user?.state]);

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <p className={styles.eyebrow}>Find help nearby</p>
        <h1 className={styles.title}>Nearest police stations</h1>
      </header>
      <div className={styles.rule} aria-hidden="true" />

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
            Location access wasn't available — showing a default location. Search a city above, or
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

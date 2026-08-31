/**
 * One-off, server-side (run by a human/CI, never the browser) fetch of every
 * amenity=police node OSM has tagged in the Mumbai Metropolitan Region.
 * Police stations don't move -- caching this removes the live Overpass
 * dependency entirely for the region almost every demo query will hit,
 * while keeping live Overpass (with its existing mirror/retry chain) as the
 * fallback for anywhere else. Re-run this script periodically by hand if
 * the data ever needs refreshing; it is NOT run automatically.
 *
 * Usage: node scripts/fetch-police-stations.mjs
 */
import { writeFileSync } from "fs";

// Bounding box (south, west, north, east) covering Mumbai city, the western
// and central suburbs, Thane, Navi Mumbai, and Kalyan -- the Mumbai
// Metropolitan Region a citizen searching "nearby stations" from within it
// would reasonably expect covered.
const BBOX = { south: 18.85, west: 72.75, north: 19.35, east: 73.15 };

const ENDPOINTS = [
  "https://overpass-api.de/api/interpreter",
  "https://lz4.overpass-api.de/api/interpreter",
  "https://overpass.kumi.systems/api/interpreter",
];

const query = `[out:json][timeout:60];node["amenity"="police"](${BBOX.south},${BBOX.west},${BBOX.north},${BBOX.east});out body;`;

function formatAddress(tags) {
  const parts = [tags["addr:housenumber"], tags["addr:street"], tags["addr:suburb"], tags["addr:city"]]
    .filter(Boolean);
  return parts.length > 0 ? parts.join(", ") : "Address not available on OpenStreetMap";
}

async function fetchFromAnyMirror() {
  let lastError;
  for (const endpoint of ENDPOINTS) {
    try {
      console.log(`Trying ${endpoint} ...`);
      // Overpass's usage policy rejects requests with no identifying
      // User-Agent (406) -- Node's fetch sends a generic one by default.
      // Not needed in the browser-side fetch elsewhere in this app: real
      // browsers always send their own.
      const res = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "text/plain",
          "User-Agent": "CaseIQ-DataFetch/1.0 (student project, one-off police-station cache build)",
        },
        body: query,
        signal: AbortSignal.timeout(50000),
      });
      if (!res.ok) throw new Error(`${endpoint} returned ${res.status}`);
      return await res.json();
    } catch (err) {
      console.warn(`  failed: ${err.message}`);
      lastError = err;
    }
  }
  throw lastError ?? new Error("all endpoints failed");
}

// Names that are essentially never a real police station's own name --
// a defensive net against upstream OSM mistagging, not a claim that the
// query itself is wrong. Found by hand (2026-08-31): OSM node 4424542678,
// name "chaitra cafe," was returned by this exact amenity=police query --
// the query correctly asked Overpass for amenity=police; the node's own
// OSM data has it mistagged. Confirmed no other entry in that fetch looked
// wrong; this filter exists in case a future re-fetch picks up a similar
// one, so it doesn't require another by-hand scan of every name.
const SUSPICIOUS_NAME_PATTERN = /\b(cafe|coffee|restaurant|hotel|hospital|school|temple|mandir|masjid|church)\b/i;

const json = await fetchFromAnyMirror();
const allElements = json.elements.filter((el) => el.lat != null && el.lon != null);
const suspicious = allElements.filter((el) => SUSPICIOUS_NAME_PATTERN.test(el.tags?.name ?? ""));
if (suspicious.length > 0) {
  console.warn(
    `WARNING: ${suspicious.length} result(s) tagged amenity=police have a suspicious name -- ` +
      `review by hand before trusting, likely upstream OSM mistagging, not excluded automatically:`,
  );
  for (const el of suspicious) console.warn(`  - ${el.id}: "${el.tags?.name}"`);
}

const stations = allElements
  .filter((el) => !SUSPICIOUS_NAME_PATTERN.test(el.tags?.name ?? ""))
  .map((el) => ({
    id: el.id,
    name: el.tags?.name || "Police Station",
    lat: el.lat,
    lon: el.lon,
    address: formatAddress(el.tags ?? {}),
  }));

const out = {
  region: "Mumbai Metropolitan Region",
  bbox: BBOX,
  fetched_at: new Date().toISOString(),
  source: "OpenStreetMap / Overpass API",
  count: stations.length,
  stations,
};

writeFileSync("src/data/police-stations-mmr.json", JSON.stringify(out, null, 2));
console.log(`Wrote ${stations.length} stations to src/data/police-stations-mmr.json`);

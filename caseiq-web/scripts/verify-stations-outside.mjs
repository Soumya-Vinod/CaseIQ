import { chromium } from "playwright";

const url = process.argv[2] ?? "http://localhost:5173";
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 390, height: 900 } });
const overpassCalls = [];
page.on("request", (r) => { if (/overpass/.test(r.url())) overpassCalls.push(r.url()); });

await page.goto(url, { waitUntil: "load" });
await page.click("text=Nearby Stations");
await page.fill("input[placeholder*='Search a city']", "Pune");
await page.click("button:has-text('Search')");
await page.waitForTimeout(15000);
await page.screenshot({ path: "outside-region-390.png" });

const noteText = await page.locator("text=Live data from OpenStreetMap").textContent().catch(() => null);
console.log("Overpass requests attempted:", overpassCalls.length, overpassCalls.slice(0, 3));
console.log("live note:", noteText);

await browser.close();

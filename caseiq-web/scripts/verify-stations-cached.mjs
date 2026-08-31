import { chromium } from "playwright";

const url = process.argv[2] ?? "http://localhost:5173";
const browser = await chromium.launch();

for (const mode of ["denied", "granted"]) {
  const context = await browser.newContext({ viewport: { width: 390, height: 900 } });

  // The case this caching exists for: Overpass completely unreachable.
  // Block every request to any Overpass mirror at the network level.
  await context.route(/overpass/, (route) => route.abort("failed"));

  if (mode === "granted") {
    await context.grantPermissions(["geolocation"]);
    await context.setGeolocation({ latitude: 19.076, longitude: 72.8777 }); // Mumbai
  }

  const page = await context.newPage();
  const overpassCalls = [];
  page.on("request", (r) => { if (/overpass/.test(r.url())) overpassCalls.push(r.url()); });

  await page.goto(url, { waitUntil: "load" });
  await page.click("text=Nearby Stations");
  await page.waitForSelector("article, li", { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(1500);

  const stationCount = await page.locator("h3").count();
  const noteText = await page.locator("text=cached from OpenStreetMap").textContent().catch(() => null);
  await page.screenshot({ path: `cached-${mode}-390.png` });

  console.log(`[${mode}] Overpass requests attempted: ${overpassCalls.length}`);
  console.log(`[${mode}] station cards rendered: ${stationCount}`);
  console.log(`[${mode}] cache note: ${noteText}`);

  await context.close();
}

await browser.close();

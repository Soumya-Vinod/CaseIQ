import { chromium } from "playwright";

const url = process.argv[2] ?? "http://localhost:5173";
const mode = process.argv[3] ?? "denied"; // "denied" or "granted"
const out = process.argv[4] ?? `stations-${mode}-390.png`;

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 390, height: 900 } });

if (mode === "granted") {
  await context.grantPermissions(["geolocation"]);
  await context.setGeolocation({ latitude: 19.076, longitude: 72.8777 }); // Mumbai
}

const page = await context.newPage();
const errors = [];
page.on("console", (msg) => { if (msg.type() === "error") errors.push(`CONSOLE: ${msg.text()}`); });
page.on("pageerror", (err) => errors.push(`PAGEERROR: ${err}`));

await page.goto(url, { waitUntil: "load" });
await page.click("text=Nearby Stations");
await page.waitForTimeout(12000); // geolocation + overpass round trip
await page.screenshot({ path: out });
console.log("errors:", JSON.stringify(errors, null, 2));
await browser.close();

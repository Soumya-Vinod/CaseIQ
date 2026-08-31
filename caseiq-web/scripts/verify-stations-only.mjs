import { chromium } from "playwright";
const url = "https://caseiq-web.vercel.app";
const browser = await chromium.launch();

for (const mode of ["denied", "granted"]) {
  const context = await browser.newContext({ viewport: { width: 390, height: 900 } });
  if (mode === "granted") {
    await context.grantPermissions(["geolocation"]);
    await context.setGeolocation({ latitude: 19.076, longitude: 72.8777 });
  }
  const page = await context.newPage();
  const errors = [];
  page.on("console", (m) => { if (m.type() === "error") errors.push(`CONSOLE: ${m.text()}`); });
  page.on("requestfailed", (r) => errors.push(`REQFAIL: ${r.url()}`));
  await page.goto(url, { waitUntil: "load" });
  await page.click("text=Nearby Stations");
  await page.waitForTimeout(28000);
  await page.screenshot({ path: `live-stations-${mode}-v2-390.png` });
  console.log(`${mode}:`, JSON.stringify(errors));
  await context.close();
}
await browser.close();

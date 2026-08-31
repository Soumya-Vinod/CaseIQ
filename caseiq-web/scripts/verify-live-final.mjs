import { chromium } from "playwright";

const url = "https://caseiq-web.vercel.app";
const browser = await chromium.launch();

// 1. Landing examples, all three, end to end.
for (const q of [
  "What is the punishment for theft?",
  "What is the punishment for defamation?",
  "What is the punishment for murder?",
]) {
  const context = await browser.newContext({ viewport: { width: 390, height: 900 } });
  const page = await context.newPage();
  const errors = [];
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  await page.goto(url, { waitUntil: "load" });
  const label = q.match(/for (\w+)\?/)[1];
  await page.click(`text=${q}`);
  await page.waitForSelector("text=Law as it stood on", { timeout: 45000 });
  const asOf = await page.locator("text=Law as it stood on").textContent();
  const hasSources = (await page.locator("text=Sources").count()) > 0;
  console.log(`[example: ${label}] as_of line: "${asOf}" | Sources rendered: ${hasSources} | errors: ${JSON.stringify(errors)}`);
  await page.screenshot({ path: `live-final-${label}-390.png` });
  await context.close();
}

// 2. Stations in Mumbai, no Overpass calls, geolocation denied.
{
  const context = await browser.newContext({ viewport: { width: 390, height: 900 } });
  const page = await context.newPage();
  const overpassCalls = [];
  page.on("request", (r) => { if (/overpass/.test(r.url())) overpassCalls.push(r.url()); });
  await page.goto(url, { waitUntil: "load" });
  await page.click("text=Nearby Stations");
  await page.waitForTimeout(3000);
  const stationCount = await page.locator("h3").count();
  console.log(`[stations, Mumbai default] Overpass calls: ${overpassCalls.length} | stations rendered: ${stationCount}`);
  await page.screenshot({ path: "live-final-stations-390.png" });
  await context.close();
}

// 3. All five tabs at 390px.
for (const tab of ["Ask", "Look up a section", "Browse by act", "News", "Nearby Stations"]) {
  const context = await browser.newContext({ viewport: { width: 390, height: 900 } });
  const page = await context.newPage();
  const errors = [];
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  await page.goto(url, { waitUntil: "load" });
  await page.click(`text=${tab}`);
  await page.waitForTimeout(1500);
  const slug = tab.replace(/\s+/g, "");
  await page.screenshot({ path: `live-final-tab-${slug}-390.png` });
  console.log(`[tab: ${tab}] errors: ${JSON.stringify(errors)}`);
  await context.close();
}

await browser.close();
console.log("done");

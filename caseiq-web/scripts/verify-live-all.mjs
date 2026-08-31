import { chromium } from "playwright";

const url = "https://caseiq-web.vercel.app";
const browser = await chromium.launch();

async function shot(context, page, tabText, out, waitSelector) {
  await page.goto(url, { waitUntil: "load" });
  await page.click(`text=${tabText}`);
  if (waitSelector) await page.waitForSelector(waitSelector, { timeout: 20000 }).catch(() => {});
  await page.waitForTimeout(1000);
  await page.screenshot({ path: out });
}

// 1. Ask tab, 390px
{
  const context = await browser.newContext({ viewport: { width: 390, height: 900 } });
  const page = await context.newPage();
  const errors = [];
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  await page.goto(url, { waitUntil: "load" });
  await page.screenshot({ path: "live-ask-390.png" });
  console.log("ASK tab errors:", JSON.stringify(errors));
  await context.close();
}

// 2. Lookup tab
{
  const context = await browser.newContext({ viewport: { width: 390, height: 900 } });
  const page = await context.newPage();
  await shot(context, page, "Look up a section", "live-lookup-390.png");
  await context.close();
}

// 3. Browse tab
{
  const context = await browser.newContext({ viewport: { width: 390, height: 900 } });
  const page = await context.newPage();
  await shot(context, page, "Browse by act", "live-browse-390.png", "text=§");
  await context.close();
}

// 4. News tab -- check real articles render
{
  const context = await browser.newContext({ viewport: { width: 390, height: 900 } });
  const page = await context.newPage();
  const errors = [];
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  page.on("requestfailed", (r) => errors.push(`REQFAIL: ${r.url()}`));
  await shot(context, page, "News", "live-news-390.png", "article");
  console.log("NEWS tab errors:", JSON.stringify(errors));
  await context.close();
}

// 5. Stations tab -- geolocation DENIED path (default context, no permission granted)
{
  const context = await browser.newContext({ viewport: { width: 390, height: 900 } });
  const page = await context.newPage();
  const errors = [];
  page.on("console", (m) => { if (m.type() === "error") errors.push(`CONSOLE: ${m.text()}`); });
  page.on("requestfailed", (r) => errors.push(`REQFAIL: ${r.url()} ${r.failure()?.errorText}`));
  page.on("response", (r) => {
    if (r.url().includes("overpass") || r.url().includes("nominatim")) {
      errors.push(`RESPONSE: ${r.status()} ${r.url().slice(0, 80)}`);
    }
  });
  await page.goto(url, { waitUntil: "load" });
  await page.click("text=Nearby Stations");
  await page.waitForTimeout(10000);
  await page.screenshot({ path: "live-stations-denied-390.png" });
  console.log("STATIONS (denied) errors/responses:", JSON.stringify(errors, null, 2));
  await context.close();
}

// 6. Stations tab -- geolocation GRANTED path
{
  const context = await browser.newContext({ viewport: { width: 390, height: 900 } });
  await context.grantPermissions(["geolocation"]);
  await context.setGeolocation({ latitude: 19.076, longitude: 72.8777 });
  const page = await context.newPage();
  const errors = [];
  page.on("console", (m) => { if (m.type() === "error") errors.push(`CONSOLE: ${m.text()}`); });
  page.on("requestfailed", (r) => errors.push(`REQFAIL: ${r.url()} ${r.failure()?.errorText}`));
  await page.goto(url, { waitUntil: "load" });
  await page.click("text=Nearby Stations");
  await page.waitForTimeout(10000);
  await page.screenshot({ path: "live-stations-granted-390.png" });
  console.log("STATIONS (granted) errors:", JSON.stringify(errors, null, 2));
  await context.close();
}

await browser.close();
console.log("done");

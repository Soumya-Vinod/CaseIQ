import { chromium } from "playwright";

const url = process.argv[2] ?? "http://localhost:5173";
const outDir = process.argv[3] ?? ".";

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
await context.grantPermissions(["geolocation"]);
await context.setGeolocation({ latitude: 19.076, longitude: 72.8777 }); // Mumbai
const page = await context.newPage();
const errors = [];
page.on("console", (msg) => { if (msg.type() === "error") errors.push(msg.text()); });
page.on("pageerror", (err) => errors.push(String(err)));

await page.goto(url, { waitUntil: "load" });
await page.waitForTimeout(300);

// Look up a section
await page.click("text=Look up a section");
await page.locator('input[placeholder], input[type="text"], input').last().fill("497");
const lookupBtn = page.getByRole("button", { name: "Look up", exact: true });
await lookupBtn.click();
await page.waitForSelector("text=Struck down", { timeout: 15000 });
await page.waitForTimeout(300);
await page.screenshot({ path: `${outDir}/full-lookup-390.png`, fullPage: true });

// Browse by act
await page.click("text=Browse by act");
await page.click("button:has-text('IPC')");
await page.waitForSelector("text=§", { timeout: 15000 });
await page.waitForTimeout(300);
await page.screenshot({ path: `${outDir}/full-browse-390.png`, fullPage: true });

// News
await page.click("text=News");
await page.waitForSelector("article", { timeout: 15000 });
await page.waitForTimeout(300);
await page.screenshot({ path: `${outDir}/full-news-390.png`, fullPage: true });

// Nearby Stations
await page.click("text=Nearby Stations");
await page.waitForTimeout(8000);
await page.screenshot({ path: `${outDir}/full-stations-390.png`, fullPage: true });

console.log("console/page errors:", JSON.stringify(errors));
await browser.close();

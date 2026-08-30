import { chromium } from "playwright";

const url = process.argv[2] ?? "http://localhost:5173";
const out = process.argv[3] ?? "browse-390.png";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 390, height: 900 } });

const errors = [];
page.on("console", (msg) => { if (msg.type() === "error") errors.push(msg.text()); });
page.on("pageerror", (err) => errors.push(String(err)));

await page.goto(url, { waitUntil: "load" });
await page.click("text=Browse by act");
await page.click("button:has-text('IPC')");
await page.waitForSelector("text=§", { timeout: 15000 });
await page.waitForTimeout(300);
// Expand the first card to prove the click-to-expand interaction works too.
await page.locator("article").first().click();
await page.waitForTimeout(200);
// Viewport-only screenshot (not fullPage) -- 200 rendered sections makes a
// full-page capture ~39000px tall and useless to actually look at.
await page.screenshot({ path: out });

console.log("console/page errors:", JSON.stringify(errors));
await browser.close();

import { chromium } from "playwright";

const url = process.argv[2] ?? "http://localhost:5173";
const out = process.argv[3] ?? "news-390.png";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 390, height: 900 } });
const errors = [];
page.on("console", (msg) => { if (msg.type() === "error") errors.push(msg.text()); });
page.on("pageerror", (err) => errors.push(String(err)));

await page.goto(url, { waitUntil: "load" });
await page.click("text=News");
await page.waitForSelector("article", { timeout: 15000 });
await page.waitForTimeout(300);
await page.screenshot({ path: out });
console.log("console/page errors:", JSON.stringify(errors));
await browser.close();

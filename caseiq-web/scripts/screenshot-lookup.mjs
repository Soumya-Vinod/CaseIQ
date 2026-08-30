import { chromium } from "playwright";

const url = process.argv[2] ?? "http://localhost:5173";
const out = process.argv[3] ?? "judicial-status-390.png";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 390, height: 900 } });

const errors = [];
page.on("console", (msg) => { if (msg.type() === "error") errors.push(msg.text()); });
page.on("pageerror", (err) => errors.push(String(err)));

await page.goto(url, { waitUntil: "load" });
// Section-lookup form defaults to IPC 497 (struck down) — just submit it.
const lookupButton = page.locator("button:has-text('Look up')");
await lookupButton.scrollIntoViewIfNeeded();
await lookupButton.click();
await page.waitForSelector("text=Struck down", { timeout: 15000 });
await page.waitForTimeout(300);

const result = page.locator("article", { hasText: "IPC" }).last();
await result.screenshot({ path: out });

console.log("console/page errors:", JSON.stringify(errors));
await browser.close();

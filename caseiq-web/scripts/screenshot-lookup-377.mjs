import { chromium } from "playwright";

const url = process.argv[2] ?? "http://localhost:5173";
const out = process.argv[3] ?? "readdown-390.png";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 390, height: 900 } });
await page.goto(url, { waitUntil: "load" });

await page.fill("input[placeholder*='Section number']", "377");
await page.locator("button:has-text('Look up')").click();
await page.waitForSelector("text=Read down", { timeout: 15000 });
await page.waitForTimeout(300);

const result = page.locator("article", { hasText: "IPC" }).last();
await result.screenshot({ path: out });
await browser.close();

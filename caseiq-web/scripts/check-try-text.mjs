import { chromium } from "playwright";
const browser = await chromium.launch();
const page = await (await browser.newContext({ viewport: { width: 390, height: 900 } })).newPage();
await page.goto("http://localhost:5173", { waitUntil: "load" });
const text = await page.locator("p", { hasText: "verified to answer" }).textContent();
console.log("rendered text:", JSON.stringify(text));
console.log("char codes around 'Try':", text.slice(0, 5).split("").map(c => c.charCodeAt(0)));
await page.screenshot({ path: "try-text-zoom.png", clip: { x: 0, y: 300, width: 390, height: 60 } });
await browser.close();

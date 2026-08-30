import { chromium } from "playwright";

const url = process.argv[2] ?? "http://localhost:5173";
const width = Number(process.argv[3] ?? 390);
const tabText = process.argv[4] ?? "Browse by act";
const out = process.argv[5] ?? `audit-${width}-${tabText.replace(/\s+/g, "")}.png`;
const actClick = process.argv[6]; // optional, e.g. "IPC" to click an act pill

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width, height: 900 } });
const errors = [];
page.on("console", (msg) => { if (msg.type() === "error") errors.push(msg.text()); });
page.on("pageerror", (err) => errors.push(String(err)));

await page.goto(url, { waitUntil: "load" });
await page.click(`text=${tabText}`);
if (actClick) {
  await page.click(`button:has-text('${actClick}')`, { timeout: 5000 }).catch(() => {});
  await page.waitForTimeout(8000);
}

const overflow = await page.evaluate(() => ({
  scrollWidth: document.documentElement.scrollWidth,
  clientWidth: document.documentElement.clientWidth,
}));
console.log(`[${width}px ${tabText}] scrollWidth=${overflow.scrollWidth} clientWidth=${overflow.clientWidth}`
  + (overflow.scrollWidth > overflow.clientWidth ? "  <-- OVERFLOW" : "  OK"));

const pillSizes = await page.$$eval("button", (els) =>
  els.filter(el => el.className.includes("actPill") || el.className.includes("submit"))
     .map((el) => { const r = el.getBoundingClientRect(); return { text: el.textContent, h: Math.round(r.height) }; })
);
console.log("interactive heights:", JSON.stringify(pillSizes));

await page.screenshot({ path: out });
console.log("console/page errors:", JSON.stringify(errors));
await browser.close();

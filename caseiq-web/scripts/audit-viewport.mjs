import { chromium } from "playwright";

const url = process.argv[2] ?? "http://localhost:5173";
const width = Number(process.argv[3] ?? 390);
const out = process.argv[4] ?? `audit-${width}.png`;

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width, height: 900 } });

const errors = [];
page.on("console", (msg) => { if (msg.type() === "error") errors.push(msg.text()); });
page.on("pageerror", (err) => errors.push(String(err)));

await page.goto(url, { waitUntil: "load" });

// Horizontal-overflow check: does the page's scrollWidth exceed the viewport?
const overflow = await page.evaluate(() => ({
  scrollWidth: document.documentElement.scrollWidth,
  clientWidth: document.documentElement.clientWidth,
}));
console.log(`[${width}px] scrollWidth=${overflow.scrollWidth} clientWidth=${overflow.clientWidth}`
  + (overflow.scrollWidth > overflow.clientWidth ? "  <-- OVERFLOW" : "  OK"));

// Tap-target check on the tab nav and (if on browse) act pills.
const tabSizes = await page.$$eval("nav button", (els) =>
  els.map((el) => { const r = el.getBoundingClientRect(); return { text: el.textContent, h: r.height }; })
);
console.log("tab heights:", JSON.stringify(tabSizes));

await page.screenshot({ path: out });
console.log("console/page errors:", JSON.stringify(errors));
await browser.close();

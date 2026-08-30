import { chromium } from "playwright";

const url = process.argv[2] ?? "http://localhost:5173";
const query = process.argv[3] ?? "What are my rights if I'm arrested without a warrant?";
const out = process.argv[4] ?? "screenshot.png";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 390, height: 844 } });

const errors = [];
page.on("console", (msg) => {
  if (msg.type() === "error") errors.push(msg.text());
});
page.on("pageerror", (err) => errors.push(String(err)));

await page.goto(url, { waitUntil: "networkidle" });
await page.fill("textarea", query);
await page.click("button[type=submit]");
await page.waitForSelector("text=Sources", { timeout: 30000 });
await page.waitForTimeout(500);
await page.screenshot({ path: out, fullPage: true });

console.log("console/page errors:", JSON.stringify(errors));
await browser.close();

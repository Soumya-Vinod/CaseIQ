import { chromium } from "playwright";

const url = process.argv[2] ?? "http://localhost:5173";
const query = process.argv[3] ?? "What is the boiling point of methane on Saturn's moon Titan?";
const out = process.argv[4] ?? "abstention-390.png";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 390, height: 844 } });

const errors = [];
page.on("console", (msg) => { if (msg.type() === "error") errors.push(msg.text()); });
page.on("pageerror", (err) => errors.push(String(err)));

await page.goto(url, { waitUntil: "load" });
await page.fill("textarea", query);
await page.click("button[type=submit]");
await page.waitForSelector("text=Not confident enough", { timeout: 30000 });
await page.waitForTimeout(400);
await page.screenshot({ path: out, fullPage: true });

console.log("console/page errors:", JSON.stringify(errors));
await browser.close();

import { chromium } from "playwright";

const url = process.argv[2] ?? "https://caseiq-web.vercel.app";
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 390, height: 844 } });

const errors = [];
page.on("console", (msg) => { if (msg.type() === "error") errors.push(`CONSOLE: ${msg.text()}`); });
page.on("pageerror", (err) => errors.push(`PAGEERROR: ${err}`));
page.on("requestfailed", (req) => errors.push(`REQUEST FAILED: ${req.url()} ${req.failure()?.errorText}`));
page.on("response", (res) => {
  if (res.url().includes("onrender.com")) errors.push(`RESPONSE: ${res.status()} ${res.url()}`);
});

await page.goto(url, { waitUntil: "load" });
await page.fill("textarea", "What is the punishment for theft?");
await page.click("button[type=submit]");

try {
  await Promise.race([
    page.waitForSelector("text=Sources", { timeout: 60000 }),
    page.waitForSelector("text=Could not reach the server", { timeout: 60000 }),
  ]);
} catch (e) {
  errors.push(`WAIT TIMEOUT: ${e.message}`);
}

await page.waitForTimeout(300);
await page.screenshot({ path: "prod-verify-390.png", fullPage: true });
console.log("errors:", JSON.stringify(errors, null, 2));
await browser.close();

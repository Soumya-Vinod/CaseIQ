import { chromium } from "playwright";
const browser = await chromium.launch();
const page = await (await browser.newContext({ viewport: { width: 390, height: 900 } })).newPage();
const errors = [];
page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
page.on("requestfailed", (r) => errors.push(`REQFAIL: ${r.url()}`));
await page.goto("https://caseiq-web.vercel.app", { waitUntil: "load" });
await page.click("text=What is the punishment for murder?");
try {
  await page.waitForSelector("text=Law as it stood on", { timeout: 45000 });
  console.log("as_of:", await page.locator("text=Law as it stood on").textContent());
} catch {
  console.log("TIMEOUT, current page text sample:");
  console.log(await page.locator("main").textContent());
}
console.log("errors:", JSON.stringify(errors));
await page.screenshot({ path: "live-final-murder-debug-390.png" });
await browser.close();

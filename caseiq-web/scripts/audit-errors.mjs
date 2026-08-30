import { chromium } from "playwright";

const url = process.argv[2] ?? "http://localhost:5173";
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 390, height: 844 } });

await page.goto(url, { waitUntil: "load" });

// Ask tab: submit with backend down.
await page.fill("textarea", "What is the punishment for theft?");
await page.click("button[type=submit]");
await page.waitForSelector("text=Could not reach the server", { timeout: 10000 });
await page.screenshot({ path: "error-ask-390.png" });

// Section lookup: submit with backend down.
await page.click("text=Look up a section");
await page.getByRole("button", { name: "Look up", exact: true }).click();
await page.waitForSelector("text=Could not reach the server", { timeout: 10000 });
await page.screenshot({ path: "error-lookup-390.png" });

// Browse: switching act triggers the debounced fetch, backend still down.
await page.click("text=Browse by act");
await page.click("button:has-text('IPC')");
await page.waitForSelector("text=Could not reach the server", { timeout: 10000 });
await page.screenshot({ path: "error-browse-390.png" });

console.log("all three error states captured");
await browser.close();

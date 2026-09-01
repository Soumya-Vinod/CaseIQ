import { chromium } from "playwright";

const url = process.argv[2] ?? "http://localhost:5173";
const outDir = process.argv[3] ?? ".";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 390, height: 844 } });

await page.goto(url, { waitUntil: "load" });
await page.getByRole("button", { name: "File a complaint" }).click();
await page.locator("select").first().selectOption("fir");
await page.locator('input[type="date"]').fill("2026-08-15");
await page.getByPlaceholder("e.g. Residence in Shivajinagar, Pune").fill("Residence in Pune");
await page.getByRole("button", { name: "Next" }).click();
await page.getByText("Your full name").locator("..").locator("input").fill("Test Complainant");
await page.getByText("Your address").locator("..").locator("textarea").fill("123 Test Street, Pune");
await page.getByRole("button", { name: "Next" }).click();
await page.getByPlaceholder("Describe the incident in your own words, as fully as you can.")
  .fill("My husband subjected me to cruelty and dowry harassment including physical beating.");
await page.getByRole("button", { name: "Next" }).click();
await page.getByRole("button", { name: "Generate draft" }).click();
await page.waitForSelector("text=Draft Ready", { timeout: 30000 });

const [download] = await Promise.all([
  page.waitForEvent("download"),
  page.getByRole("link", { name: "Download PDF" }).click(),
]);
const savePath = `${outDir}/downloaded-complaint.pdf`;
await download.saveAs(savePath);
console.log("suggested filename:", download.suggestedFilename());
console.log("saved to:", savePath);

await browser.close();

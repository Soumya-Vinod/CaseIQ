import { chromium } from "playwright";

const url = process.argv[2] ?? "http://localhost:5173";
const outDir = process.argv[3] ?? ".";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
const errors = [];
page.on("console", (msg) => { if (msg.type() === "error") errors.push(msg.text()); });
page.on("pageerror", (err) => errors.push(String(err)));

await page.goto(url, { waitUntil: "load" });
await page.waitForTimeout(300);

// Switch to the "File a complaint" tab
await page.getByRole("button", { name: "File a complaint" }).click();
await page.waitForTimeout(200);
await page.screenshot({ path: `${outDir}/complaint-step1-390.png`, fullPage: true });

// Step 1: Incident
await page.locator("select").first().selectOption("fir");
await page.locator('input[type="date"]').fill("2026-08-15");
await page.getByPlaceholder("e.g. Residence in Shivajinagar, Pune").fill("Residence in Pune");
await page.getByPlaceholder("e.g. Shivajinagar Police Station").fill("Shivajinagar Police Station");
await page.getByRole("button", { name: "Next" }).click();
await page.waitForTimeout(150);
await page.screenshot({ path: `${outDir}/complaint-step2-390.png`, fullPage: true });

// Step 2: Parties
await page.getByText("Your full name").locator("..").locator("input").fill("Test Complainant");
await page.getByText("Your address").locator("..").locator("textarea").fill("123 Test Street, Pune, Maharashtra");
await page.getByText("Accused / other party details").locator("..").locator("textarea")
  .fill("Husband Rajesh Kumar and mother-in-law Sunita Kumar");
await page.getByRole("button", { name: "Next" }).click();
await page.waitForTimeout(150);
await page.screenshot({ path: `${outDir}/complaint-step3-390.png`, fullPage: true });

// Step 3: Narrative
await page.getByPlaceholder("Describe the incident in your own words, as fully as you can.")
  .fill("My husband and his family have been subjecting me to cruelty and harassment over dowry demands, including physical beating, for the past six months.");
await page.getByPlaceholder("e.g. medical report, photographs, messages")
  .fill("Medical report from hospital visit dated 2026-08-10");
await page.getByRole("button", { name: "Next" }).click();
await page.waitForTimeout(150);
await page.screenshot({ path: `${outDir}/complaint-step4-390.png`, fullPage: true });

// Step 4: Relief
await page.getByPlaceholder("e.g. Registration of an FIR, a protection order, return of property")
  .fill("Registration of FIR and protection order");
await page.getByRole("button", { name: "Generate draft" }).click();
await page.waitForSelector("text=Draft Ready", { timeout: 30000 });
await page.waitForTimeout(500);
await page.screenshot({ path: `${outDir}/complaint-result-390.png`, fullPage: true });

console.log("console/page errors:", JSON.stringify(errors));
await browser.close();

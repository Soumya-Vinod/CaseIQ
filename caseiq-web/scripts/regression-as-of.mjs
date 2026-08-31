/**
 * Regression check for a bug that couldn't be reproduced (2026-08-31): a
 * screenshot once showed "Law as it stood on 21 Aug 2026" when the API's
 * as_of was actually 2026-08-31 -- a ten-day gap, not the one-day shift a
 * UTC-midnight-in-IST parsing bug would produce. Root cause not found
 * (checked: no client-side date defaulting -- as_of comes only from the API
 * response; no backend cache layer on the query path; the formatter itself
 * reproduces correctly in isolation, twice). Per instruction: this asserts
 * the rendered date against the API's own as_of on every run, so a
 * recurrence fails loudly instead of silently. Exits non-zero on mismatch.
 *
 * Usage: node scripts/regression-as-of.mjs [frontendUrl] [backendUrl]
 */
import { chromium } from "playwright";

const frontendUrl = process.argv[2] ?? "http://localhost:5173";
const backendUrl = process.argv[3] ?? "http://127.0.0.1:8000";
const query = "What is the punishment for murder?";

function formatAsOf(iso) {
  // Mirrors src/components/AnswerBriefing.tsx's formatAsOf exactly -- if
  // that function's formatting ever changes, this must change with it.
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

// 1. Canonical value, straight from the API, bypassing the UI entirely.
const apiRes = await fetch(`${backendUrl}/api/v1/legal/query`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ query, language: "en", session_id: "" }),
});
if (!apiRes.ok) {
  console.error(`FAIL: API request failed with ${apiRes.status}`);
  process.exit(1);
}
const apiData = await apiRes.json();
const expected = formatAsOf(apiData.as_of);

// 2. What the real UI actually renders for the same query.
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 390, height: 900 } });
await page.goto(frontendUrl, { waitUntil: "load" });
await page.fill("textarea", query);
await page.click("button[type=submit]");
await page.waitForSelector("text=Law as it stood on", { timeout: 30000 });
const rendered = await page.textContent("text=Law as it stood on");
await browser.close();

const renderedDate = rendered?.replace("Law as it stood on ", "").trim();

if (renderedDate === expected) {
  console.log(`PASS: rendered "${renderedDate}" matches API as_of "${apiData.as_of}" (${expected})`);
  process.exit(0);
} else {
  console.error(
    `FAIL: UI rendered "${renderedDate}" but API as_of was "${apiData.as_of}" ` +
      `(expected formatted value: "${expected}")`,
  );
  process.exit(1);
}

#!/usr/bin/env node
// Programmatic version of the check a phone had to do twice
// (docs/evaluation.md, "mobileBar sharing the flex row with content" /
// "Media query range syntax..."): at each mobile width, with the drawer
// closed, the page's main content must be exactly as wide as the
// viewport. A screenshot a person looks at does not assert this -- both
// bugs this check exists for shipped past months of passing screenshots
// specifically because nothing ever compared `main`'s computed width
// against `window.innerWidth` programmatically. This does, cheaply,
// against the real built bundle (via `vite preview`, not the dev server).
//
// What this CAN catch: a layout defect visible to any browser, including
// Playwright's own evergreen Chromium -- exactly the class the mobileBar
// bug was (a flex-sibling sizing bug, nothing to do with CSS parsing).
// What this CANNOT catch: the CSS-media-query-range-syntax class of bug --
// that needs an engine below Chrome 104, and Playwright never ships one.
// That class is guarded separately, statically, by
// check-css-media-queries.mjs against the built CSS text itself. Run both;
// neither substitutes for the other.

import { chromium } from "playwright";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { setTimeout as delay } from "node:timers/promises";

const root = fileURLToPath(new URL("..", import.meta.url));
const PORT = 4174; // distinct from a dev `vite preview` a contributor might already have open
const BASE_URL = `http://localhost:${PORT}`;
const WIDTHS = [360, 390, 414];
const MOBILE_UA =
  "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36";

async function waitForServer(url, timeoutMs = 20_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(url);
      if (res.ok) return;
    } catch {
      /* not up yet */
    }
    await delay(250);
  }
  throw new Error(`check-mobile-layout: preview server never became reachable at ${url}`);
}

async function checkWidth(browser, width) {
  const failures = [];
  const context = await browser.newContext({
    viewport: { width, height: 844 },
    isMobile: true,
    hasTouch: true,
    userAgent: MOBILE_UA,
  });
  const page = await context.newPage();
  try {
    await page.goto(BASE_URL, { waitUntil: "networkidle" });

    // Drawer closed: main must be exactly as wide as the viewport, and the
    // page must not scroll horizontally at all.
    const closed = await page.evaluate(() => ({
      innerWidth: window.innerWidth,
      mainWidth: document.querySelector("main")?.getBoundingClientRect().width ?? null,
      scrollWidth: document.documentElement.scrollWidth,
      hamburgerVisible: !!document.querySelector('button[aria-label="Open navigation menu"]'),
    }));
    if (closed.mainWidth !== closed.innerWidth) {
      failures.push(
        `${width}px closed: main width ${closed.mainWidth}px !== viewport width ${closed.innerWidth}px ` +
          "-- content is not full width with the drawer closed (this is exactly the mobileBar/flex-sibling bug's signature).",
      );
    }
    if (closed.scrollWidth > closed.innerWidth) {
      failures.push(
        `${width}px closed: horizontal scroll present (scrollWidth ${closed.scrollWidth}px > innerWidth ${closed.innerWidth}px).`,
      );
    }
    if (!closed.hamburgerVisible) {
      failures.push(`${width}px closed: hamburger button not found -- mobile nav bar isn't rendering at all.`);
    }

    // Open the drawer: still no horizontal scroll, and the drawer should
    // actually be on-screen (identity transform), not stuck off-canvas.
    await page.click('button[aria-label="Open navigation menu"]');
    await page.waitForTimeout(300);
    const opened = await page.evaluate(() => {
      const navs = [...document.querySelectorAll('nav[aria-label="Main"]')];
      const drawer = navs[navs.length - 1];
      return {
        scrollWidth: document.documentElement.scrollWidth,
        innerWidth: window.innerWidth,
        drawerTransform: drawer ? getComputedStyle(drawer).transform : null,
      };
    });
    if (opened.scrollWidth > opened.innerWidth) {
      failures.push(`${width}px open: horizontal scroll present while the drawer is open.`);
    }
    if (opened.drawerTransform && opened.drawerTransform !== "none" && !opened.drawerTransform.startsWith("matrix(1, 0, 0, 1, 0, 0")) {
      failures.push(`${width}px open: drawer transform is "${opened.drawerTransform}" -- doesn't look on-screen.`);
    }

    // Close it again: content must return to full width, not stay squeezed.
    await page.click('button[aria-label="Close menu"]');
    await page.waitForTimeout(300);
    const reClosed = await page.evaluate(() => ({
      innerWidth: window.innerWidth,
      mainWidth: document.querySelector("main")?.getBoundingClientRect().width ?? null,
    }));
    if (reClosed.mainWidth !== reClosed.innerWidth) {
      failures.push(
        `${width}px re-closed: main width ${reClosed.mainWidth}px !== viewport width ${reClosed.innerWidth}px ` +
          "after closing the drawer again -- content did not return to full width.",
      );
    }
  } finally {
    await context.close();
  }
  return failures;
}

// `shell: true` rather than resolving npx.cmd/npx by hand -- the more
// portable option across Windows/macOS/Linux CI runners for spawning a
// package-manager-provided binary.
const previewProcess = spawn("npx vite preview --port " + PORT + " --strictPort", {
  cwd: root,
  stdio: "pipe",
  shell: true,
});

let allFailures = [];
try {
  await waitForServer(BASE_URL);
  const browser = await chromium.launch();
  try {
    for (const width of WIDTHS) {
      const failures = await checkWidth(browser, width);
      allFailures.push(...failures);
    }
  } finally {
    await browser.close();
  }
} finally {
  previewProcess.kill();
}

if (allFailures.length > 0) {
  console.error(`check-mobile-layout: FAIL -- ${allFailures.length} issue(s) found:\n`);
  for (const f of allFailures) console.error(`  - ${f}`);
  process.exit(1);
}

console.log(
  `check-mobile-layout: OK -- at ${WIDTHS.join("/")}px, content is full width with the drawer closed, ` +
    "no horizontal scroll, and the drawer opens/closes correctly.",
);

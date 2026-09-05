#!/usr/bin/env node
// Guards against the exact regression documented in docs/evaluation.md
// ("Media query range syntax silently breaks mobile layout on real
// devices"): a CSS build tool (lightningcss, via Vite's default cssMinify)
// silently rewriting `@media (max-width: 859px)` into the newer range
// syntax `@media (width<=859px)`, which real low-end/older Android
// browsers don't parse -- the whole @media block becomes invalid and is
// dropped, so the rule inside it never applies. Playwright can never catch
// this (its bundled Chromium always supports whatever syntax the build
// emits), so this has to be a static check on the actual shipped CSS.
//
// Two independent checks, because they catch different failure classes:
//   1. Range syntax specifically -- the regression that already happened.
//   2. Per-condition occurrence COUNT, source vs built -- a dropped block
//      (from a future minifier change, a different transform, a merge bug)
//      can happen without ever using range syntax at all, and check 1
//      alone would sail past it silently.
//
// Run automatically as the last step of `npm run build`; also run in CI
// (.github/workflows/frontend-ci.yml) on every push/PR so a regression
// fails the build there too, not just on someone's machine.

import { readFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { join, extname } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
const srcDir = join(root, "src");
const distDir = join(root, "dist");

function walkCssFiles(dir) {
  if (!existsSync(dir)) return [];
  const out = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const stat = statSync(full);
    if (stat.isDirectory()) out.push(...walkCssFiles(full));
    else if (extname(entry) === ".css") out.push(full);
  }
  return out;
}

// Extract each `@media (<condition>)` this project's own CSS authors,
// normalised (whitespace stripped) so "max-width: 859px" and the built,
// minified "max-width:859px" compare equal. Returns a multiset (condition
// -> occurrence count) rather than a plain set, because two separate
// source blocks sharing the same condition (QueryPage.module.css has two
// `min-width: 960px` blocks) must each survive into the build -- a set
// would hide one of the two silently disappearing.
// Strip CSS block comments before scanning source -- a comment explaining a
// media query in prose (this file's own vite.config.ts/App.module.css
// comments do exactly this) contains the literal text `@media (...)` and
// would otherwise be miscounted as a real rule. Built/minified files never
// have comments, so this only matters for the source side, but it's cheap
// to apply everywhere.
function stripComments(text) {
  return text.replace(/\/\*[\s\S]*?\*\//g, "");
}

function extractConditions(files) {
  const counts = new Map();
  for (const file of files) {
    const text = stripComments(readFileSync(file, "utf8"));
    const re = /@media\s*\(([^)]*)\)/g;
    let m;
    while ((m = re.exec(text))) {
      const normalised = m[1].replace(/\s+/g, "");
      counts.set(normalised, (counts.get(normalised) ?? 0) + 1);
    }
  }
  return counts;
}

// A standard media feature never contains `<` or `>` -- only the CSS Media
// Queries Level 4 range syntax does (`width<=859px`, `400px < width <
// 700px`, etc). So any `<`/`>` between `@media` and the block's opening
// `{` is exactly the tell for a range-syntax comparison, regardless of
// which media feature it's applied to.
function findRangeSyntax(files) {
  const offenders = [];
  for (const file of files) {
    const text = stripComments(readFileSync(file, "utf8"));
    const re = /@media[^{]*[<>][^{]*\{/g;
    let m;
    while ((m = re.exec(text))) {
      offenders.push({ file, snippet: m[0].slice(0, 120) });
    }
  }
  return offenders;
}

if (!existsSync(distDir)) {
  console.error(
    "check-css-media-queries: dist/ does not exist -- run `vite build` before this check.",
  );
  process.exit(1);
}

const sourceFiles = walkCssFiles(srcDir);
const builtFiles = walkCssFiles(distDir);

const rangeSyntaxHits = findRangeSyntax(builtFiles);

// Built CSS is one concatenated, whitespace-stripped blob per file (Vite
// bundles third-party CSS -- e.g. leaflet's, which has its own @media
// print -- alongside ours), so a raw total-@media-count comparison against
// src/**/*.css would false-fail on vendor CSS we don't author and don't
// control. Instead: every condition WE wrote must survive into the build,
// the same number of times, in its original (non-range) form. This still
// catches a silently dropped or duplicated block -- the failure this
// check exists for -- without caring how many unrelated @media blocks
// ship alongside ours.
const sourceConditions = extractConditions(sourceFiles);
const builtText = builtFiles.map((f) => readFileSync(f, "utf8")).join("\n");
const builtTextNoSpace = builtText.replace(/\s+/g, "");

let failed = false;

if (rangeSyntaxHits.length > 0) {
  failed = true;
  console.error(
    `check-css-media-queries: FAIL -- found ${rangeSyntaxHits.length} media query/queries using ` +
      "CSS range syntax (e.g. `width<=859px`) in the built CSS. This needs Chrome/Chrome-for-" +
      "Android 104+, Safari 16.4+, Samsung Internet 20+ -- unsupported on real budget/older " +
      "Android devices this project targets (docs/caseiq-industry-readiness.md G13), even though " +
      "Playwright's evergreen Chromium always supports it and will never fail this locally.\n" +
      "Likely cause: vite.config.ts's build.cssTarget was removed, weakened, or overridden. See " +
      "docs/evaluation.md's \"Media query range syntax\" finding.",
  );
  for (const { file, snippet } of rangeSyntaxHits) {
    console.error(`  ${file}: ${snippet}...`);
  }
}

for (const [condition, expectedCount] of sourceConditions) {
  const needle = `@media(${condition}){`;
  const re = new RegExp(needle.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "g");
  const actualCount = (builtTextNoSpace.match(re) ?? []).length;
  if (actualCount !== expectedCount) {
    failed = true;
    console.error(
      `check-css-media-queries: FAIL -- source authors "@media (${condition})" ${expectedCount} ` +
        `time(s) across src/**/*.css, but the built CSS contains it ${actualCount} time(s). A ` +
        "block going missing (or gaining an unexpected duplicate) between source and the built " +
        "bundle is exactly the failure shape of the range-syntax regression, just possibly via a " +
        "different transform. Diff dist/assets/*.css against src/**/*.css for this condition.",
    );
  }
}

if (failed) process.exit(1);

const totalConditions = [...sourceConditions.values()].reduce((a, b) => a + b, 0);
console.log(
  `check-css-media-queries: OK -- all ${totalConditions} of this project's own @media condition(s) ` +
    "survived into the built CSS unchanged, none using range syntax.",
);

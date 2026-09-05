#!/usr/bin/env node
// Validates every statutory quote in src/data/situationGuides.ts against the
// live corpus -- the fix for the garbled-quote bug (docs/evaluation.md,
// "a quote sourced from the offence-attributes table, not section_text"),
// built to run BEFORE a guide ships, not found by hand after.
//
// SCOPE, decided deliberately, not just implicitly: this checks ONLY
// `GuideEntitlement.quote` and `GuideRecognitionItem.quote` -- the two
// content shapes that carry an `act`+`section` and render as a bordered
// blockquote with a citation badge (SituationGuideDetail.tsx). The
// "practicalTips" spoken-script lines (`GuidePracticalTip`) are explicitly
// OUT of scope: that type has no `quote`/`act`/`section` field at all, so a
// script line is structurally incapable of carrying an implied citation --
// TypeScript would refuse to compile one that tried. Six of those scripts
// currently mention a section NUMBER in the sentence itself ("under section
// 173") without being a statutory quote; they render in the plain dashed
// practical box, never a blockquote, and this validator correctly has
// nothing to check them against, because they never claimed to quote the
// law.
//
// NORMALISATION, per instruction -- whitespace/line-breaks only, nothing
// that could hide a real mismatch: both the quote and the fetched
// section_text have internal whitespace runs (including newlines, and the
// literal double-space/line-wrap artifacts the PDF-derived corpus text
// carries) collapsed to a single space, and are trimmed. No case-folding,
// no punctuation stripping, no smart-quote normalisation -- if a quote is
// wrong, this must fail, not quietly pass.
//
// ELLIPSIS QUOTES: an elided quote ("first part … second part") is split on
// the ellipsis and each segment must appear in the normalised section_text,
// IN ORDER (segment 2's match must start at or after segment 1's match
// ends) -- not just "both segments exist somewhere in the text", which
// would pass a fabricated join of two unrelated fragments.
//
// Usage: node scripts/validate-guide-quotes.mjs [--api-base <url>]
// Exits non-zero if any quote fails, so this can gate a deploy.

const args = process.argv.slice(2);
const apiBaseIdx = args.indexOf("--api-base");
const API_BASE =
  apiBaseIdx !== -1 ? args[apiBaseIdx + 1] : process.env.VALIDATE_API_BASE || "https://caseiq.onrender.com";

const { SITUATION_GUIDES } = await import("../src/data/situationGuides.ts");

function normalise(text) {
  return text.replace(/\s+/g, " ").trim();
}

function checkQuote(quote, sectionText) {
  const normQuote = normalise(quote);
  const normText = normalise(sectionText);
  const ELLIPSIS = "…";

  if (!normQuote.includes(ELLIPSIS)) {
    return { ok: normText.includes(normQuote), reason: normText.includes(normQuote) ? "" : "substring not found" };
  }

  const segments = normQuote.split(ELLIPSIS).map((s) => s.trim()).filter(Boolean);
  let searchFrom = 0;
  for (const seg of segments) {
    const idx = normText.indexOf(seg, searchFrom);
    if (idx === -1) {
      return { ok: false, reason: `segment not found in order: "${seg.slice(0, 60)}..."` };
    }
    searchFrom = idx + seg.length;
  }
  return { ok: true, reason: "" };
}

const sectionCache = new Map();
async function fetchSectionText(act, section) {
  const key = `${act}/${section}`;
  if (sectionCache.has(key)) return sectionCache.get(key);
  const url = `${API_BASE}/api/v1/knowledge/sections/${act}/${section}`;
  const res = await fetch(url);
  if (!res.ok) {
    const err = { error: `HTTP ${res.status}` };
    sectionCache.set(key, err);
    return err;
  }
  const data = await res.json();
  const result = { text: data.section_text };
  sectionCache.set(key, result);
  return result;
}

let totalChecked = 0;
let totalFailed = 0;
const failures = [];

for (const guide of SITUATION_GUIDES) {
  console.log(`\n=== ${guide.title} (${guide.slug}) ===`);

  const quoteSources = [
    ...guide.entitlements.map((e) => ({ kind: "entitlement", label: e.heading, act: e.act, section: e.section, quote: e.quote })),
    ...(guide.recognition?.items ?? []).map((it) => ({ kind: "recognition", label: it.label, act: it.act, section: it.section, quote: it.quote })),
  ];

  for (const q of quoteSources) {
    totalChecked++;
    const fetched = await fetchSectionText(q.act, q.section);
    if (fetched.error) {
      totalFailed++;
      const msg = `FETCH ERROR (${fetched.error}) -- ${q.act} §${q.section}`;
      console.log(`  ✗ [${q.kind}] ${q.label.slice(0, 55)}`);
      console.log(`      ${msg}`);
      failures.push({ guide: guide.slug, ...q, reason: msg });
      continue;
    }
    const result = checkQuote(q.quote, fetched.text);
    if (result.ok) {
      console.log(`  ✓ [${q.kind}] ${q.act} §${q.section} -- "${q.quote.slice(0, 55)}${q.quote.length > 55 ? "..." : ""}"`);
    } else {
      totalFailed++;
      console.log(`  ✗ [${q.kind}] ${q.act} §${q.section} -- "${q.quote.slice(0, 55)}..."`);
      console.log(`      ${result.reason}`);
      failures.push({ guide: guide.slug, ...q, reason: result.reason });
    }
  }
}

console.log(`\n${totalChecked} quotes checked, ${totalChecked - totalFailed} passed, ${totalFailed} failed.`);

if (totalFailed > 0) {
  console.log("\nFAILURES:");
  for (const f of failures) {
    console.log(`  - ${f.guide} / ${f.kind} / ${f.act} §${f.section}: ${f.reason}`);
    console.log(`    quote: "${f.quote}"`);
  }
  process.exit(1);
}
process.exit(0);

/**
 * Some parsers (LegacyActParser, older acts) fold the marginal note into
 * both `title` and the start of the body text — e.g. IPC §497 has
 * title="Adultery.—Whoever has sexual intercourse…" AND section_text
 * starting "497. Adultery.—Whoever has sexual intercourse…". Rendering
 * both reads as a UI bug, not a citation. This is a display heuristic
 * only — it doesn't touch the data, just skips a redundant heading when
 * the body already leads with the same text.
 */
export function isRedundantTitle(title: string, body: string): boolean {
  const t = title.trim().toLowerCase();
  if (!t) return true;
  const bodyHead = body.slice(0, t.length + 20).toLowerCase();
  return bodyHead.includes(t);
}

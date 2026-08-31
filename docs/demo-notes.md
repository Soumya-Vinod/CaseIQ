# Demo notes

Read once beforehand. Not a script — the answers you'd reconstruct under pressure anyway, written
down so you don't have to.

## Opening story: the withdrawn bill

Lead with this, not the retrieval miss rate — it's the strongest evidence of rigour in the
project, not a caveat.

For a stretch of this project's history, the PDF being ingested and cited as "BNS 2023" was not
the Bharatiya Nyaya Sanhita — it was **Bill No. 121 of 2023**, withdrawn from the Lok Sabha on
12 December 2023 and replaced by different legislation before anything was enacted. The withdrawn
Bill has 356 sections; the enacted Act has 358, and at least three offence definitions differ
between them. Nothing in the original ingestion pipeline checked whether a source file was an
enacted Act or a withdrawn Bill — it embedded and served whatever text was on disk.

**The point to land**: this was caught by systematic provenance checking — reading each source
PDF's own cover page and cross-checking it — not because someone noticed a wrong answer. That's
the difference between a project that gets debugged when it visibly breaks and one that checks its
own inputs before trusting them. Fix: a provenance manifest recording each file's verified act
number and source, and a guard that now refuses to ingest anything not positively confirmed as an
enacted Act. The withdrawn Bill is preserved, quarantined, not deleted — for audit.

Full writeup: `docs/incidents/2026-08-09-withdrawn-bns-bill-ingested.md`.

## "Retrieval misses 25% of your golden set — why?"

> Measured, not estimated — 11 of 44 hand-verified questions miss even in the top 10. The cause is
> that our embeddings come from a fast, offline hashing function, not a trained semantic model, so
> a colloquial question ("anticipatory bail") and the statute's own formal phrasing ("direction for
> grant of bail to a person apprehending arrest") don't always share enough words to match. But the
> system knows what it doesn't know: when it can't ground an answer, it says so and points to legal
> aid instead of guessing — which is exactly what the earlier prototype didn't do, and why it once
> cited a section number that doesn't exist. The 25% is a real, honest number; the abstention
> design means it fails safe, not silently.

## "Why not just use a real embedding model, then?"

The honest answer, not a dodge — this is a resource constraint with a known fix, not an unknown:

> I did — Gemini's embedding API was the original plan. It has a free-tier cap of 1,000 requests
> per day, and this corpus is 2,155 sections. Ingestion hit that cap partway through, twice. At
> that point the choice was a complete corpus on weak embeddings or a partial corpus on strong
> ones, and I took the complete corpus — a system that can't answer about two-fifths of criminal
> law at all is a worse demo than one that's measurably imperfect on all of it. A paid Gemini key,
> or a self-hosted sentence-transformer model, closes this gap directly — it's the highest-leverage
> change available, higher than any further threshold or prompt tuning, and it's scoped and
> documented, not an open question.

## One line each, in case asked directly

- **What does "Part K" do?** Every statutory section is bitemporal — it carries its own in-force
  date and version number, so asking "as of" a past date returns the version of the law that
  actually applied then, and a struck-down provision (like IPC §497) is excluded from every normal
  answer path except the one explicit lookup designed to still show it, correctly labelled dead
  law.
- **Why does abstention matter?** Because the alternative — an LLM answering from its own memory
  when retrieval finds nothing relevant — is exactly how the project's first-ever test invented a
  section number that doesn't exist. Abstaining honestly is the harder-looking demo state and the
  correct one.

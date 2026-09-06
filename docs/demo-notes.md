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

## "Retrieval used to miss 25% of your golden set — what happened?"

**This one changed under us — a real fix landed 2026-09-06, not just a mitigation.** The old
answer defended a known, measured limitation; the current one is a demonstrated result, which is a
stronger thing to say in a demo, not a weaker one:

> We measured it, found the actual cause, and fixed it rather than working around it again. The
> original embeddings came from a fast, offline hashing function, not a trained semantic model, so
> a colloquial question ("anticipatory bail") and the statute's own formal phrasing didn't always
> share enough words to match — 11 of 44 hand-verified questions missed even in the top 10. We
> replaced that hashing function with a real, self-hosted sentence-embedding model
> (`all-MiniLM-L6-v2`, run locally via ONNX Runtime — no cloud API, no per-request cost, chosen
> specifically to fit inside our hosting tier's memory limit, which we measured before committing
> to it rather than assumed). Retrieval quality on the same 44 questions went from 0.705 Recall@5 /
> 0.387 MRR to **0.909 / 0.730** — only 2 of 44 miss now. And the abstention mechanism this system
> leans on to avoid guessing got sharper too: the canonical nonsense query we use to prove
> abstention works went from a similarity score that barely cleared its own threshold to one nearly
> 3.5x below it — the difference between "usually catches it" and "clearly catches it."

## "So retrieval is solved now?"

No, and worth saying plainly rather than overclaiming a clean win:

> Real embeddings, not a classifier. Two of 44 golden-set questions still miss entirely. A civil-law
> question with nothing on point in this corpus still isn't cleanly separable from a real criminal
> question by similarity score alone — it's much closer to nonsense than it used to be, but not
> reliably below the same cutoff a real question clears, so we still lean on a separate,
> independent check for that specific case rather than similarity alone. And a handful of common
> phrasings (filing an FIR, several dowry-related terms) still need a small hand-curated assist even
> with real embeddings — down from fourteen such phrasings to nine, which is itself a measured
> result, not a guess.

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

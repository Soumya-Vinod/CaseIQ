# `caseiq-backend` (Django): LLM features, as they actually behaved, before removal

`caseiq-backend` — the original Django REST Framework implementation — is being deleted now that
`caseiq-fastapi` has fully replaced it. Before deletion, its LLM-touching code is recorded here as
it actually ran, checked directly against the code (and, for the two dead ends below, against
what actually happens when the code path executes), not assumed from a method name or an endpoint
being wired. Same discipline this project has applied to itself throughout `docs/evaluation.md` —
most recently the directive-language entry (2026-09-19), which caught a Django feature
(`EthicsRule`) that looked real — schema, seed data, admin registration — and was never queried by
anything. Two more instances of exactly that shape turned up doing this check, recorded below.

**Preserved at commit `6a08d18044bc477be22ee1d7476df19d2107e9c7`** (`feat: switching to fastapi`,
2026-08-09 14:02:37 +0530 — the last commit that touched `caseiq-backend`; working tree clean at
the time this document was written). `git show 6a08d18:caseiq-backend/<path>` recovers any file
named below after the folder is gone.

## `services/groq_service.py` — the one LLM client

Groq, model `llama-3.3-70b-versatile`, temperature 0.1, JSON-mode prompts, up to 3 retries. Nine
methods; checked every one against every file in `apps/` and `services/` for an actual call site,
not just assumed wired because it looked like an endpoint's obvious backing method.

**Wired and working, as far as static inspection can confirm:**
- `is_dark_query` — a hardcoded 12-phrase harm-facilitation list (`'how to kill'`, `'how to make a
  bomb'`, `'child abuse'`, etc.), checked with plain substring matching before any LLM call. Wired
  into `apps/legal_query/views.py`'s `process_legal_query` endpoint as a gate.
- `detect_language` — one LLM call, replies `en`/`hi`/`mr`/`ta`/`te`. Wired, and notably the same
  5-language list `caseiq-fastapi`'s own `llm_service.detect_language` uses — confirming that
  number wasn't invented during the port (see `docs/evaluation.md`'s complaint-disclaimer entry,
  2026-09-19, which relies on this same fact from the other direction).
- `process_legal_query` — the core RAG flow. Retrieval here is **not** semantic search:
  `_build_rag_context` takes the query's first 6 non-stopword words and runs a plain
  `Q(icontains=...)` OR-filter across `BNSSSection.section_title` / `.section_text` / `.category`,
  no ranking, top 6 rows. `_detect_topic_change` (a crime-keyword-overlap heuristic, not an LLM
  call) picks between two prompt variants — a structured JSON schema for a new topic, a freeform
  conversational JSON reply for a follow-up. This is the direct ancestor of `caseiq-fastapi`'s
  `/legal/query` — the single largest architectural change between them is retrieval: real
  pgvector-backed semantic search over an actually-populated embeddings column replaced this
  keyword filter, not just a reimplementation of the same mechanism in a new framework.
- `generate_related_questions`, `generate_legal_timeline`, `generate_rights_card`,
  `generate_scenario_simulation`, `verify_citation` — each has its own dedicated endpoint
  (`apps/legal_query/urls.py`: `timeline/`, `rights-card/`, `simulate/`, `verify-citation/`), and
  each is called with arguments matching its method signature — no mismatch found, unlike the next
  entry. Whether the prompts themselves produced good output was never re-tested here (would need
  a live `GROQ_API_KEY` and a real call, out of scope for a static check before deletion); what's
  confirmed is that the plumbing between view and method agrees.

**Wired, but broken on every real call — confirmed by reading both sides, not assumed from the
disclaimer text sitting right there in the response:**
- `generate_complaint_draft` — `apps/complaints/views.py`'s `generate_complaint_draft` view calls
  it as `groq_service.generate_complaint_draft(complaint_dict, language)`, **two** positional
  arguments. The method itself is `def generate_complaint_draft(self, complaint_data):` — **one**
  parameter. Every real invocation raises `TypeError: generate_complaint_draft() takes 2
  positional arguments but 3 were given`, caught by the view's own broad `except Exception`, which
  sets the complaint back to `status='draft'` and returns HTTP 500 with the exception text as
  `detail`. This endpoint could never have produced a complaint draft in this codebase's committed
  history — the ready-to-return disclaimer string in the success-path `Response(...)` a few lines
  below was consequently just as unreachable. (Unrelated to `caseiq-fastapi`'s own complaint
  disclaimer work, `docs/evaluation.md` 2026-09-19 — that entry ported the *content* of Django's
  seeded disclaimer strings, which were real data; this finding is about the generation endpoint
  that would have sat in front of them, which was not.)

**Defined, never called anywhere — dead code, not a hidden feature:**
- `tag_news_with_sections`, `generate_embeddings_text` — grepped `apps/` and `services/` directly
  for both names; no call site for either. `generate_embeddings_text` is a one-line stub
  (`return text[:8000] if text else ''`) — truncation, not an embedding, consistent with it never
  having been wired to anything that needed a real one.

## `services/gemini_service.py` — imported, but the file is empty

`apps/knowledge_base/views.py`'s `semantic_search` endpoint does
`from services.gemini_service import gemini_service` inside a `try` block and calls
`gemini_service.generate_query_embedding(query)`. **`services/gemini_service.py` is a zero-byte
file** — confirmed by reading it directly. Every real call to this endpoint hits an `ImportError`
inside that `try`, is caught by the view's own `except Exception`, logs `"Semantic search fallback
to keyword"`, and silently returns a plain `title__icontains` keyword match instead, labelled
`"search_type": "keyword_fallback"` in the response — a client calling this endpoint in good faith
has no way to know semantic search never ran.

Independently — so this isn't only about the missing service — `LegalProvision.embedding`
(`apps/knowledge_base/models.py`) is commented out in the model itself: `# embedding column - will
be enabled after pgvector install`. Even a working `gemini_service` would have had no vector
column to write embeddings into or query against; `semantic_search`'s own `L2Distance('embedding',
query_embedding)` call references a model field that does not exist. Semantic search was never
functional at any point in this codebase's history, on either side of the pipeline — no embeddings
were ever generated, no column existed to store them, and the one service meant to generate them
on query was an empty file — despite a dedicated `pgvector_src/` custom Dockerfile built for the
infrastructure layer underneath it. Same shape as the `EthicsRule` and `generate_complaint_draft`
findings above: something that looks wired from the call site, or from the infrastructure sitting
next to it, with nothing real connecting the two ends.

## For the record: what replaced these in `caseiq-fastapi`

Real pgvector-backed semantic search over an actually-populated embeddings column
(`all-MiniLM-L6-v2-onnx`, with Gemini re-embedding in progress — `docs/model-card.md`); grounding
verification, punishment-claim verification, and directive-language detection as real, tested,
wired detection layers with persisted stats counters — none of which Django ever had running,
regardless of what its schema or seed data implied; and a complaint-draft endpoint whose view
calls its own generation function with the arguments that function actually accepts.

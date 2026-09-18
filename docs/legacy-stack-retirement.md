# The retired Django stack (`caseiq-backend` + `caseiq-frontend`): what's actually in it, before removal

`caseiq-backend` (Django REST Framework) and `caseiq-frontend` (React) — the original
implementation, both halves — are being deleted now that `caseiq-fastapi` + `caseiq-web` have
fully replaced them. Before deletion, what each actually did is recorded here as it actually ran or
rendered, checked directly against the code, not assumed from a method name, an endpoint being
wired, or a component existing. Same discipline this project has applied to itself throughout
`docs/evaluation.md` — most recently the directive-language entry (2026-09-19), which caught a
Django feature (`EthicsRule`) that looked real — schema, seed data, admin registration — and was
never queried by anything. Three more instances of that same "looks wired, isn't" shape turned up
doing this check (`docs/evaluation.md`'s own named-pattern entry, 2026-09-19, catalogues all four
together); this document has the full detail behind each.

**Preserved at commit `6a08d18044bc477be22ee1d7476df19d2107e9c7`** (`feat: switching to fastapi`,
2026-08-09 14:02:37 +0530 — the last commit that touched either folder; working tree clean at the
time this document was written). `git show 6a08d18:caseiq-backend/<path>` (or `caseiq-frontend/`)
recovers any file named below after both folders are gone.

---

# Part 1 — `caseiq-backend` (Django): LLM features, as they actually behaved

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

---

# Part 2 — `caseiq-frontend` (React): audited the same way, not a straight delete

Checked before deletion, same three questions asked of `caseiq-backend`: does anything else still
structurally depend on this folder, is there built UI here with no equivalent in `caseiq-web` yet
(which would make returning to a deferred feature more expensive to lose than to keep documented),
and is there hand-authored content — copy, translations, form structure — with no equivalent
anywhere else.

**Structural references**: none functional. Grepped every workflow, config, and doc for
`caseiq-frontend`; the five hits (`caseiq-claude-code-prompt.md`, `caseiq-expo-deployment.md`,
`caseiq-industry-readiness.md`, `deployment.md`, `docs/evaluation.md`) are all descriptive —
`caseiq-industry-readiness.md`'s own Part G already states the plan directly: *"that app is wired
to the retired Django API and is being **replaced**, not repaired ... treat the old app as
reference for information architecture only ... not as code to port."* Same last commit as
`caseiq-backend` (`6a08d180`), same clean working tree.

## UI built here with no `caseiq-web` equivalent yet

Four components, not three — `ChatPage.jsx` wires up a fourth deferred-feature panel
(`CitationVerifier.jsx`, backing `verify_citation`) alongside the three named going in. All four are
real, complete, and call endpoints already confirmed arity-matched in Part 1 (unlike
`generate_complaint_draft`) — this is what makes returning to any of these three cheaper than
starting from the API schema alone:

- **`components/ai/LegalTimeline.jsx`** — renders `generate_legal_timeline`'s array (`phase`,
  `event`, `description`, `law_reference`, `time_frame`, `status`) as a vertical stepper with
  completed/current/upcoming states, connecting line, and a badge per event for its law reference.
- **`components/ai/RightsCard.jsx`** — renders `generate_rights_card`'s shape (`situation_title`,
  `rights[]` — each with `right`/`explanation`/`law_reference`/`what_to_say`, `emergency_contacts[]`,
  `important_warning`) as a shareable card with a one-click "copy as text" action.
- **`components/ai/ScenarioSimulator.jsx`** — a free-text "what if" input plus four preset prompts
  (*"What if I don't file the FIR?"*, etc.), calls `simulateScenario`, renders `scenario_title` /
  `legal_outcome` / `what_to_do` from the response.
- **`components/ai/CitationVerifier.jsx`** — the UI for `verify_citation`; not previously traced to
  a frontend before this pass — found only by grepping every reference to the endpoint name, the
  same "check the call site, not the method list" discipline as everything else in Part 1.

All four are wired into `pages/ChatPage.jsx` as collapsible tool panels beneath the chat, triggered
by buttons in a toolbar row (`"What-If Simulator"`, etc.) — the toggling/collapse state management
around them (`toolsCollapsed`, `activeTool`) is itself real UI logic, not just the four leaf
components in isolation, if this is ever picked back up as a reference.

## Hand-authored content with no `caseiq-web` equivalent

**Real gap, worth preserving directly, not just noting**: `context/LanguageContext.jsx` is a
complete Hindi and Marathi translation dictionary for the application's own UI chrome — app name,
every nav label, buttons, placeholders, the disclaimer string, the welcome message. Checked
`caseiq-web` directly for anything playing this role: nothing — no `LanguageContext`, no
`uiLanguage` state, no translations object anywhere in it. `caseiq-web`'s only language handling is
per-content (the complaint draft's own `en`/`hi`/`mr`/`ta` field, `docs/evaluation.md` 2026-09-19)
— the interface itself has never been anything but English in the current stack. This is exactly
the category that nearly went missing once already in this session (the complaint disclaimers'
hi/mr text, `docs/evaluation.md`, same date) — real, hand-written translation work, unrecorded
anywhere outside this file about to be deleted. Reproduced here in full so it survives the delete,
not merely flagged as existing:

```js
// context/LanguageContext.jsx — UI-chrome strings only (nav, buttons, placeholders,
// disclaimer, welcome message), en/hi/mr. Never wired to caseiq-web; no ta entry ever
// existed here either (unlike the complaint-draft language field, which does support ta).
const translations = {
  en: {
    appName: 'CaseIQ', tagline: 'AI-Powered Legal Knowledge', home: 'Home',
    aiAssistant: 'AI Assistant', firDraft: 'FIR Draft', lawExplorer: 'Law Explorer',
    legalNews: 'Legal News', education: 'Education', dashboard: 'Dashboard',
    history: 'History', settings: 'Settings', signIn: 'Sign In', signOut: 'Sign Out',
    createAccount: 'Create Account', askQuery: 'Ask a Legal Question',
    queryPlaceholder: 'Type your legal question...', sendButton: 'Send',
    generateFIR: 'Generate FIR Draft', downloadPDF: 'Download PDF', clearChat: 'Clear Chat',
    noHistory: 'No history yet', loading: 'Loading...',
    disclaimer: '⚠️ CaseIQ provides legal knowledge only, not legal advice.',
    welcomeMessage: '👋 Welcome to CaseIQ. Ask any legal question about Indian law.',
  },
  hi: {
    appName: 'केसआईक्यू', tagline: 'AI-संचालित कानूनी ज्ञान', home: 'होम',
    aiAssistant: 'AI सहायक', firDraft: 'FIR ड्राफ्ट', lawExplorer: 'कानून खोजक',
    legalNews: 'कानूनी समाचार', education: 'शिक्षा', dashboard: 'डैशबोर्ड',
    history: 'इतिहास', settings: 'सेटिंग्स', signIn: 'साइन इन', signOut: 'साइन आउट',
    createAccount: 'खाता बनाएं', askQuery: 'कानूनी प्रश्न पूछें',
    queryPlaceholder: 'अपना कानूनी प्रश्न टाइप करें...', sendButton: 'भेजें',
    generateFIR: 'FIR ड्राफ्ट बनाएं', downloadPDF: 'PDF डाउनलोड करें', clearChat: 'चैट साफ करें',
    noHistory: 'अभी तक कोई इतिहास नहीं', loading: 'लोड हो रहा है...',
    disclaimer: '⚠️ केसआईक्यू केवल कानूनी जानकारी प्रदान करता है, कानूनी सलाह नहीं।',
    welcomeMessage: '👋 केसआईक्यू में आपका स्वागत है। भारतीय कानून के बारे में कोई भी प्रश्न पूछें।',
  },
  mr: {
    appName: 'केसआयक्यू', tagline: 'AI-चालित कायदेशीर ज्ञान', home: 'मुखपृष्ठ',
    aiAssistant: 'AI सहाय्यक', firDraft: 'FIR मसुदा', lawExplorer: 'कायदा शोधक',
    legalNews: 'कायदेशीर बातम्या', education: 'शिक्षण', dashboard: 'डॅशबोर्ड',
    history: 'इतिहास', settings: 'सेटिंग्ज', signIn: 'साइन इन', signOut: 'साइन आउट',
    createAccount: 'खाते तयार करा', askQuery: 'कायदेशीर प्रश्न विचारा',
    queryPlaceholder: 'तुमचा कायदेशीर प्रश्न टाइप करा...', sendButton: 'पाठवा',
    generateFIR: 'FIR मसुदा तयार करा', downloadPDF: 'PDF डाउनलोड करा', clearChat: 'चॅट साफ करा',
    noHistory: 'अद्याप इतिहास नाही', loading: 'लोड होत आहे...',
    disclaimer: '⚠️ केसआयक्यू फक्त कायदेशीर माहिती देते, कायदेशीर सल्ला नाही।',
    welcomeMessage: '👋 केसआयक्यूमध्ये आपले स्वागत आहे। भारतीय कायद्याबद्दल कोणताही प्रश्न विचारा।',
  },
};
```

**Checked and ruled out, not skipped** — two more places this category of finding could plausibly
have been hiding, both came back clean:
- `components/fir/FIRWizard.jsx`'s field placeholders looked hand-authored enough to be worth
  comparing directly (`"Describe the incident in detail — what happened, how it happened, sequence
  of events..."`, `"Physical description — age, height, clothing, identifying marks..."`). Compared
  against `caseiq-web/src/pages/ComplaintPage.tsx`'s own placeholders field-by-field: it already has
  comparably thoughtful, arguably plainer-language copy of its own (`"Describe the incident in your
  own words, as fully as you can."`). No gap — different words, not lost words.
- `pages/EducationPage.jsx` and `pages/LawExplorerPage.jsx` — grepped both for any hardcoded content
  string; neither has one. Both are purely API/DB-driven, so there's nothing here beyond what
  `apps/awareness/management/commands/seed_education.py` already gave `docs/evaluation.md`'s
  situation-guide-folding entry (2026-09-19) directly from the source.
- Noted in passing, not a finding: `hooks/useSpeechInput.js` has a one-line BCP-47 locale map
  (`{ en: 'en-IN', hi: 'hi-IN', mr: 'mr-IN', ta: 'ta-IN' }`) for the Web Speech API — trivial enough
  that reproducing it here would overstate its value, but named so nothing gets assumed unchecked.

## For the record: what `caseiq-web` has instead

A `ComplaintPage.tsx` that already covers every field `FIRDraftPage.jsx` did, plus complaint types
beyond FIR (`written_complaint`, `magistrate_complaint`, `consumer_complaint`, `cyber_complaint`)
and its own independently-written placeholder guidance. What it does **not** have: any of the four
tool panels above, or any UI-chrome translation layer at all — both real, named gaps, not silent
ones, should either become a priority later.

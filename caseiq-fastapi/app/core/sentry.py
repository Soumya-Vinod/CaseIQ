"""Error capture only -- no tracing/performance monitoring, no structlog
pipeline. Scoped explicitly (docs/evaluation.md, observability entry) after
this project found four real, live, self-announcing-to-nobody failures by
hand in one session (rate limiting enforcing nothing, a test suite writing
to production, RAG truncation losing a quarter of the corpus, an ungrounded
answer reaching a user) -- production had no tracing, no error aggregation,
and no alerting, so the next one would have waited for someone to look.

DELIBERATELY NOT a structlog integration: Sentry has no first-party structlog
processor the way it does for stdlib `logging`, and piping every
`logger.warning(...)` call into Sentry as an event would burn the free
tier's error quota on routine, EXPECTED warnings (a single Groq-key
cooldown, a single stripped citation) that already have their own counters
(grounding_stats, punishment_verification_stats, citation_verification_
stats) and their own threshold-based alerting
(scripts/check_observability_thresholds.py + .github/workflows/
observability-alerts.yml) -- rate-based, not per-event, which is the right
shape for signals that are individually normal and only matter in
aggregate. Sentry is for the OTHER shape: an unhandled exception or a total
outage, which has no natural "rate" and needs a stack trace, not a count.
A handful of explicit `sentry_sdk.capture_exception()` calls at the sites
that actually matter (see below), not a blanket hook.

DELIBERATELY NO TRACING: `traces_sample_rate=0.0`, explicit rather than
relying on the SDK's own default (which is also off, but this project's own
style is to say the deliberate thing rather than lean on an undocumented
default -- see this file's sibling modules). Tracing is the part of Sentry
that adds real per-request overhead (span creation on every request); plain
error capture only activates when an exception is actually raised. Measured
directly before this was wired in, not assumed: ~5MB on disk, ~1s one-time
process-startup cost, ~0.6ms per `capture_exception` call -- negligible
against a 512MB Render free instance that already pays a 30-60s cold start
after spin-down, and zero cost on the request path when nothing goes wrong.

`send_default_pii=False`, explicit: this project does deliberate PII
redaction throughout (app.services.pii_redaction) before anything leaves
the process for Groq or gets stored -- Sentry's own default request-context
capture must not become a second, unredacted channel for the same data.
Left as the SDK's own default value on purpose (True is not an option this
project would ever choose), stated here so a future reader doesn't have to
go find out what the default is.
"""
from __future__ import annotations

import sentry_sdk

from app.core.build_info import get_build_info
from app.core.config import settings


def configure_sentry() -> None:
    """Call as the FIRST thing in app.main's lifespan, before
    configure_logging() and certainly before the startup assertions
    (assert_embedding_config_matches_corpus / assert_domain_gate_matches_
    embedder) -- those are deliberately allowed to crash the process (see
    their own callers' comments: "must crash startup, not degrade to a
    logged warning nobody reads"), and Sentry has to already be initialised
    for the explicit capture wrapped around them (main.py's lifespan) to
    have anywhere to send that crash. A no-op when SENTRY_DSN is unset --
    dev, CI, and tests never need this.
    """
    build = get_build_info()
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENV,
        release=build.get("git_commit"),
        traces_sample_rate=0.0,
        send_default_pii=False,
    )

"""TEMPORARY -- added 2026-09-17 solely to verify Sentry's unhandled-
exception capture path actually reaches the real dashboard in production
(docs/evaluation.md, observability entry: "a capture path nobody has
watched fire is the same untested-guardrail shape as everything else").
Certainty over waiting on a probabilistic trigger (a concurrent-load burst
against /legal/query was tried first and didn't reproduce a 503).

MUST BE REMOVED in the same session, once the triggered event is confirmed
in the Sentry dashboard. This file plus its one registration line in
app/api/v1/router.py are the entire footprint -- both removed together,
nothing else touched.

Deliberately unauthenticated (raises immediately, touches no data, reads
nothing, lives for minutes) but path-namespaced with an unguessable marker
so an automated scanner hitting it during its short life can't be confused
with the deliberate, one-time trigger this exists for.
"""
from fastapi import APIRouter

router = APIRouter(
    prefix="/_sentry_verification_temporary_do_not_ship", tags=["TEMPORARY -- delete me"],
)


@router.get("/trigger-9f3a1c7e")
async def trigger_sentry_verification_temporary() -> None:
    raise RuntimeError(
        "SENTRY_VERIFICATION_TEMPORARY_TRIGGER -- if you see this in Sentry, the unhandled-"
        "exception capture path works end to end. This route must be removed immediately after "
        "confirming (docs/evaluation.md, observability entry)."
    )

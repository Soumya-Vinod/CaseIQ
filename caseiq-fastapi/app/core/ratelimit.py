"""In-memory rate limiting via slowapi.

FIXED 2026-09-08 (docs/evaluation.md): this file existed, was wired into
main.py's exception handler and app.state, and looked configured -- but
was never actually enforcing anything (no `SlowAPIMiddleware`, no
`@limiter.limit` on any route -- confirmed by grep, not assumed) and
carried two latent bugs that would have surfaced the moment either half
got finished alone:

  1. `storage_uri` pointed at `settings.REDIS_URL`, which docs/deployment.md
     already confirms is unprovisioned on Render -- turning this on as-is
     would have pointed at a Redis that was never there.
  2. `key_func` was slowapi's own `get_remote_address`, which reads
     `request.client.host` directly and does NOT check `X-Forwarded-For`.
     Behind Render's proxy that's Render's own internal address, not the
     real client -- every anonymous user (most traffic) would have
     collapsed onto ONE shared key, either rate-limiting everyone as a
     single client or (depending on which side of the limit that shared
     counter landed on) not limiting anyone at all.

Sixth instance of this project's own recurring finding: a config that
looks right and produces valid-looking behaviour -- here, a route that
returns 200s exactly like it always did -- while either doing nothing or
doing the wrong thing, both indistinguishable from "working" until
someone actually checks. See docs/evaluation.md for the other five.

Render's free tier is a single instance today -- in-memory (no
`storage_uri` at all, the real slowapi default, not a fallback) is the
correct store for that. If this ever scales to two or more instances,
each keeps its own independent counter with no coordination -- the
effective limit becomes leaky and unpredictable (not simply "twice as
generous": depends on how the load balancer happens to distribute a
given client's requests across instances). Fix at that point is pointing
`storage_uri` at a real Redis -- a config change this file is already
shaped for, not a redesign.
"""
from __future__ import annotations

import jwt
from fastapi import Request
from slowapi import Limiter

from app.api.deps import client_ip
from app.core.security import decode_token


def rate_limit_key(request: Request) -> str:
    """user_id when a valid access token is present, client_ip() otherwise
    -- covers both authenticated and (the majority) anonymous traffic with
    what's actually available on the request, per docs/evaluation.md's
    scoping. Decodes the JWT directly rather than depending on
    app.api.deps.optional_user (which needs a DB round-trip to load the
    User row) -- slowapi's key_func runs synchronously, and a rate-limit
    key doesn't need the full user object, just the token's own `sub`
    claim. An invalid/expired token degrades to the IP key, same
    graceful-fallback shape as optional_user's own AuthError -> None.
    """
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        try:
            payload = decode_token(auth[7:].strip())
            if payload.get("type") == "access" and payload.get("sub"):
                return f"user:{payload['sub']}"
        except jwt.PyJWTError:
            pass
    return f"ip:{client_ip(request) or 'unknown'}"


limiter = Limiter(
    key_func=rate_limit_key,
    default_limits=["200/hour"],
    headers_enabled=True,
)

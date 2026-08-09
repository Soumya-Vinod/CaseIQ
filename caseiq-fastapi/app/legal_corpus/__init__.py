"""Legal corpus subsystem: provenance, parsing, validation, and (Part K) versioning.

Peer to app/services/, not nested under it. services/ reads corpus metadata
(retrieval filters on valid_from/valid_to, answers cite content_as_on) but this
package must never import from app.services -- that keeps the dependency arrow
one-way. Both the API and the arq worker (K5's change-detection pipeline) import
from here directly; scripts/ only holds thin CLI entrypoints.
"""

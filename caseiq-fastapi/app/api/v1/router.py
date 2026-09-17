from fastapi import APIRouter

from app.api.v1 import (
    admin_corpus, audit, auth, awareness, complaints, conversations, knowledge, legal,
    sentry_verification_temporary,  # TEMPORARY -- see that module's own docstring, remove together
)

api_router = APIRouter()
for module in (
    auth, legal, conversations, knowledge, complaints, awareness, audit, admin_corpus,
    sentry_verification_temporary,
):
    api_router.include_router(module.router)

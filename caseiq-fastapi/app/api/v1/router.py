from fastapi import APIRouter

from app.api.v1 import admin_corpus, audit, auth, awareness, complaints, knowledge, legal

api_router = APIRouter()
for module in (auth, legal, knowledge, complaints, awareness, audit, admin_corpus):
    api_router.include_router(module.router)

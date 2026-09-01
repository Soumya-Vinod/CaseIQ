"""Ground complaint drafting in retrieval, same as /legal/query.

Why: the complaint endpoint (app/api/v1/complaints.py) took a caller-supplied
`applicable_sections: list[str]` straight from the request body and handed it
to the LLM as fact, with no retrieval call anywhere in the path -- flagged in
app/schemas/complaint.py (2026-08-11) but never fixed. A section number in a
complaint a user might actually file is a worse place for an invented
citation than a wrong search result. Fixed 2026-09-01: `applicable_sections`
is no longer client input; the server runs the same semantic_search() used by
/legal/query against the incident narrative and stores what it actually
found.

`retrieved_sections` mirrors QueryResponse.retrieved_sections (app/models/legal.py)
exactly -- same shape (full section dicts: act, section, title, snippet,
judicial_status, similarity), same reason: the PDF and the frontend "sources"
panel must be reproducible from the stored row alone, without re-querying
retrieval, since Render's disk is ephemeral (see docs/deployment.md) and a
download request may hit a container that never ran the original POST.

`applicable_sections` (existing JSONB column) is kept but repurposed: it now
holds the short citation strings derived FROM retrieved_sections server-side
(e.g. "BNS 85", "IPC 498A"), for the PDF's compact "Sections:" line -- never
written from client input again.

Revision ID: 0006_complaint_grounding
Revises: 0005_fulltext_search
Create Date: 2026-09-01 00:00:00
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0006_complaint_grounding"
down_revision = "0005_fulltext_search"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "complaints",
        sa.Column("retrieved_sections", JSONB, nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("complaints", "retrieved_sections")

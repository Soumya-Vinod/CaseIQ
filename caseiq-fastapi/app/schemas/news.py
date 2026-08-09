from datetime import datetime
from uuid import UUID

from app.schemas.common import ORMModel


class NewsOut(ORMModel):
    id: UUID
    title: str
    source: str
    source_url: str
    summary: str
    published_at: datetime
    tags: list
    is_featured: bool

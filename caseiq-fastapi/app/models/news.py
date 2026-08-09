from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import Timestamped, UUIDPk


class LegalNewsArticle(UUIDPk, Timestamped, Base):
    __tablename__ = "legal_news_articles"

    title: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(200), default="")
    source_url: Mapped[str] = mapped_column(String(500), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    published_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True))
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    language: Mapped[str] = mapped_column(String(5), default="en")

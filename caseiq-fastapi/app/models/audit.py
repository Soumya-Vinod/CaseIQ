from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import Timestamped, UUIDPk


class AuditLog(UUIDPk, Timestamped, Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_user_created", "user_id", "created_at"),
        Index("ix_audit_action", "action"),
    )

    user_id: Mapped[PgUUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(100))
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    # A truncated HMAC-SHA256 of the request IP, keyed with SECRET_KEY -- never
    # the raw address. IP is personal data under India's DPDP Act 2023; a keyed
    # hash still lets the same IP be correlated across rows (abuse/rate-limit
    # investigation) without storing something reversible. See
    # app/middleware/request_context.py:_hash_ip.
    ip_hash: Mapped[str | None] = mapped_column(String(45))
    request_id: Mapped[str | None] = mapped_column(String(64))

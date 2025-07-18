from .base import Base, CommonMixin
import uuid
from sqlalchemy import (
    Column,
    String,
    Integer,
    ForeignKey,
    UniqueConstraint,
    ForeignKeyConstraint,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
    declarative_mixin,
    declared_attr,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID


class Session(Base, CommonMixin):
    __tablename__ = "sessions"
    __table_args__ = (
        # This ensures id is unique within each project
        UniqueConstraint("project_id", "id"),
        ForeignKeyConstraint(
            ["project_id", "space_id"],
            ["spaces.project_id", "spaces.id"],
            ondelete="CASCADE",
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        primary_key=True,
    )
    space_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    configs: Mapped[dict] = mapped_column(JSONB, nullable=True)

    space: Mapped["Space"] = relationship(  # type: ignore
        "Space",
        foreign_keys=[project_id, space_id],
        back_populates="sessions",
    )

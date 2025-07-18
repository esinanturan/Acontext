from .base import Base, CommonMixin
import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
    declarative_mixin,
    declared_attr,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from ..pydantic.orm.base import ProjectRow


class Project(Base, CommonMixin):
    __tablename__ = "projects"
    __use_pydantic__ = ProjectRow

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    configs: Mapped[dict] = mapped_column(JSONB, nullable=True)

    spaces: Mapped[list["Space"]] = relationship(  # type: ignore
        "Space", back_populates="project", cascade="all, delete-orphan"
    )

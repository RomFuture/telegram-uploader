from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UploadSessionRow(Base):
    __tablename__ = "upload_sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    profile_name: Mapped[str] = mapped_column(Text, nullable=False)
    encryption_key: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)

    source_items: Mapped[list["SourceItemRow"]] = relationship(back_populates="session")


class SourceItemRow(Base):
    __tablename__ = "source_items"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    session_id: Mapped[UUID] = mapped_column(ForeignKey("upload_sessions.id", ondelete="CASCADE"))
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)

    session: Mapped[UploadSessionRow] = relationship(back_populates="source_items")
    archive_volumes: Mapped[list["ArchiveVolumeRow"]] = relationship(back_populates="source_item")


class ArchiveVolumeRow(Base):
    __tablename__ = "archive_volumes"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    source_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_items.id", ondelete="CASCADE"),
    )
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    local_path: Mapped[str] = mapped_column(Text, nullable=False)
    part_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    external_file_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_message_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_download_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)

    source_item: Mapped[SourceItemRow] = relationship(back_populates="archive_volumes")

from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Index, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """SQLAlchemy ORM 基类。"""


class VideoRow(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    path: Mapped[str] = mapped_column(Text, unique=True)
    title: Mapped[str] = mapped_column(Text)
    fps: Mapped[float] = mapped_column(Float)
    frame_count: Mapped[int] = mapped_column(Integer)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    duration_seconds: Mapped[float] = mapped_column(Float)
    people_count: Mapped[int] = mapped_column(Integer)
    timeline_path: Mapped[str] = mapped_column(Text)
    diagnostics_json: Mapped[str] = mapped_column(Text, default="{}")
    original_filename: Mapped[str | None] = mapped_column(Text)
    series_name: Mapped[str] = mapped_column(Text, default="")
    source_path: Mapped[str | None] = mapped_column(Text)
    source_directory: Mapped[str] = mapped_column(Text, default="")
    deleted_at: Mapped[str | None] = mapped_column(Text)

    people: Mapped[list["PersonRow"]] = relationship(cascade="all, delete-orphan")
    tracks: Mapped[list["TrackRow"]] = relationship(cascade="all, delete-orphan")
    segments: Mapped[list["SegmentRow"]] = relationship(cascade="all, delete-orphan")
    face_crops: Mapped[list["FaceCropRow"]] = relationship(cascade="all, delete-orphan")


class PersonRow(Base):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"))
    person_id: Mapped[int] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(Text)
    global_person_id: Mapped[str | None] = mapped_column(Text)
    appearances: Mapped[int] = mapped_column(Integer)
    total_duration: Mapped[float] = mapped_column(Float)
    detection_count: Mapped[int] = mapped_column(Integer)
    representative_face_path: Mapped[str | None] = mapped_column(Text)
    representative_timestamp: Mapped[float | None] = mapped_column(Float)
    representative_frame_index: Mapped[int | None] = mapped_column(Integer)
    hidden: Mapped[int] = mapped_column(Integer, default=0)


class TrackRow(Base):
    __tablename__ = "tracks"
    __table_args__ = (UniqueConstraint("video_id", "track_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"))
    track_id: Mapped[int] = mapped_column(Integer)
    person_id: Mapped[int | None] = mapped_column(Integer)
    start: Mapped[float] = mapped_column(Float)
    end: Mapped[float] = mapped_column(Float)
    detection_count: Mapped[int] = mapped_column(Integer)
    representative_face_path: Mapped[str | None] = mapped_column(Text)
    representative_bbox_json: Mapped[str] = mapped_column(Text, default="null")
    representative_confidence: Mapped[float | None] = mapped_column(Float)
    representative_timestamp: Mapped[float | None] = mapped_column(Float)
    representative_frame_index: Mapped[int | None] = mapped_column(Integer)
    embedding_dim: Mapped[int] = mapped_column(Integer, default=0)
    embedding_norm: Mapped[float] = mapped_column(Float, default=0.0)


class TrackDetectionRow(Base):
    __tablename__ = "track_detections"
    __table_args__ = (
        Index("idx_track_detections_video_time", "video_id", "timestamp"),
        Index("idx_track_detections_video_track", "video_id", "track_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"))
    track_id: Mapped[int] = mapped_column(Integer)
    person_id: Mapped[int | None] = mapped_column(Integer)
    frame_index: Mapped[int] = mapped_column(Integer)
    timestamp: Mapped[float] = mapped_column(Float)
    bbox_json: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)


class SegmentRow(Base):
    __tablename__ = "segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"))
    person_id: Mapped[int] = mapped_column(Integer)
    start: Mapped[float] = mapped_column(Float)
    end: Mapped[float] = mapped_column(Float)
    detection_count: Mapped[int] = mapped_column(Integer)
    track_ids: Mapped[str] = mapped_column(Text)
    clip_path: Mapped[str | None] = mapped_column(Text)


class FaceCropRow(Base):
    __tablename__ = "face_crops"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"))
    person_id: Mapped[int | None] = mapped_column(Integer)
    track_id: Mapped[int | None] = mapped_column(Integer)
    path: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
    timestamp: Mapped[float | None] = mapped_column(Float)
    frame_index: Mapped[int | None] = mapped_column(Integer)


class GlobalPersonRow(Base):
    __tablename__ = "global_people"

    global_person_id: Mapped[str] = mapped_column(Text, primary_key=True)
    label: Mapped[str | None] = mapped_column(Text)
    representative_face_path: Mapped[str | None] = mapped_column(Text)
    representative_timestamp: Mapped[float | None] = mapped_column(Float)
    representative_frame_index: Mapped[int | None] = mapped_column(Integer)
    observation_count: Mapped[int] = mapped_column(Integer, default=0)
    confirmed_count: Mapped[int] = mapped_column(Integer, default=0)
    total_duration: Mapped[float] = mapped_column(Float, default=0.0)
    deleted_at: Mapped[str | None] = mapped_column(Text)


class GlobalObservationRow(Base):
    __tablename__ = "global_observations"
    __table_args__ = (UniqueConstraint("global_person_id", "video_path", "local_person_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    global_person_id: Mapped[str] = mapped_column(Text)
    video_id: Mapped[int | None] = mapped_column(Integer)
    video_path: Mapped[str] = mapped_column(Text)
    local_person_id: Mapped[int] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(Text)
    representative_face_path: Mapped[str | None] = mapped_column(Text)
    representative_timestamp: Mapped[float | None] = mapped_column(Float)
    representative_frame_index: Mapped[int | None] = mapped_column(Integer)
    appearances: Mapped[int] = mapped_column(Integer)
    total_duration: Mapped[float] = mapped_column(Float)
    detection_count: Mapped[int] = mapped_column(Integer)
    confirmed: Mapped[int] = mapped_column(Integer, default=0)
    rejected: Mapped[int] = mapped_column(Integer, default=0)
    hidden: Mapped[int] = mapped_column(Integer, default=0)


class FourViewAssetRow(Base):
    __tablename__ = "global_person_four_view_assets"
    __table_args__ = (Index("idx_four_view_assets_person", "global_person_id", "id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    global_person_id: Mapped[str] = mapped_column(Text)
    label: Mapped[str] = mapped_column(Text)
    image_path: Mapped[str] = mapped_column(Text)
    reference_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[str] = mapped_column(Text, server_default=func.current_timestamp())


class GlobalPersonActionRow(Base):
    __tablename__ = "global_person_actions"
    __table_args__ = (Index("idx_global_person_actions_person", "global_person_id", "id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    global_person_id: Mapped[str] = mapped_column(Text)
    action: Mapped[str] = mapped_column(Text)
    payload_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, server_default=func.current_timestamp())


class ReviewActionRow(Base):
    __tablename__ = "review_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"))
    action: Mapped[str] = mapped_column(Text)
    payload_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, server_default=func.current_timestamp())


class AnalyzeJobRow(Base):
    __tablename__ = "analyze_jobs"

    job_id: Mapped[str] = mapped_column(Text, primary_key=True)
    status: Mapped[str] = mapped_column(Text)
    stage: Mapped[str] = mapped_column(Text)
    progress: Mapped[float] = mapped_column(Float)
    message: Mapped[str] = mapped_column(Text)
    payload_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, server_default=func.current_timestamp())
    updated_at: Mapped[str] = mapped_column(Text, server_default=func.current_timestamp())

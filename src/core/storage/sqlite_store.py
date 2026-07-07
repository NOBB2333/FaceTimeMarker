from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import case, delete, func, or_, select
from sqlalchemy.orm import Session

from core.storage.database import make_engine, make_session_factory, session_scope
from core.storage.orm_models import (
    AnalyzeJobRow,
    Base,
    FaceCropRow,
    FourViewAssetRow,
    GlobalObservationRow,
    GlobalPersonActionRow,
    GlobalPersonRow,
    PersonRow,
    ReviewActionRow,
    SegmentRow,
    TrackDetectionRow,
    TrackRow,
    VideoRow,
)


class SQLiteStore:
    """结果库兼容入口。

    名称保留为 SQLiteStore 是为了兼容旧调用方；新实现优先通过 SQLAlchemy ORM 访问。
    """

    def __init__(self, path: Path, url: str | None = None) -> None:
        """初始化数据库连接并创建表结构。"""
        self.path = path
        self.engine = make_engine(path, url)
        self.session_factory = make_session_factory(self.engine)
        if self.engine.dialect.name == "sqlite":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def list_videos(
        self,
        *,
        include_deleted: bool = False,
        only_deleted: bool = False,
    ) -> list[dict[str, Any]]:
        """列出所有已导入的视频。"""
        stmt = select(VideoRow)
        if only_deleted:
            stmt = stmt.where(VideoRow.deleted_at.is_not(None))
        elif not include_deleted:
            stmt = stmt.where(VideoRow.deleted_at.is_(None))
        stmt = stmt.order_by(VideoRow.id.desc())
        with session_scope(self.session_factory) as session:
            rows = session.scalars(stmt).all()
        return [_video_model_payload(row) for row in rows]

    def update_video_metadata(
        self,
        video_id: int,
        *,
        title: str | None = None,
        series_name: str | None = None,
        original_filename: str | None = None,
        source_path: str | None = None,
        source_directory: str | None = None,
    ) -> dict[str, Any]:
        """更新视频的展示标题和系列信息。"""
        with session_scope(self.session_factory) as session:
            row = session.get(VideoRow, video_id)
            if row is None:
                raise ValueError("video not found")
            next_title = title.strip() if title is not None and title.strip() else row.title
            next_series_name = (
                series_name.strip() if series_name is not None else row.series_name
            )
            next_original_filename = (
                original_filename.strip()
                if original_filename is not None and original_filename.strip()
                else row.original_filename
            )
            next_source_path = (
                source_path.strip()
                if source_path is not None and source_path.strip()
                else row.source_path
            )
            next_source_directory = (
                source_directory.strip()
                if source_directory is not None and source_directory.strip()
                else (
                    str(Path(next_source_path).parent)
                    if source_path is not None and source_path.strip()
                    else row.source_directory
                )
            )
            row.title = next_title
            row.series_name = next_series_name
            row.original_filename = next_original_filename
            row.source_path = next_source_path
            row.source_directory = next_source_directory
            return _video_model_payload(row)

    def get_video(self, video_id: int, *, include_deleted: bool = False) -> dict[str, Any] | None:
        """根据 ID 获取单个视频信息。"""
        with session_scope(self.session_factory) as session:
            row = session.get(VideoRow, video_id)
            if row is None or (row.deleted_at is not None and not include_deleted):
                return None
            return _video_model_payload(row)

    def move_video_to_trash(self, video_id: int) -> dict[str, Any]:
        """把视频移入回收站，保留所有分析数据以便还原。"""
        deleted_at = datetime.now(UTC).isoformat()
        with session_scope(self.session_factory) as session:
            row = session.get(VideoRow, video_id)
            if row is None:
                raise ValueError("video not found")
            row.deleted_at = deleted_at
            return _video_model_payload(row)

    def restore_video(self, video_id: int) -> dict[str, Any]:
        """从回收站恢复视频。"""
        with session_scope(self.session_factory) as session:
            row = session.get(VideoRow, video_id)
            if row is None:
                raise ValueError("video not found")
            row.deleted_at = None
            return _video_model_payload(row)

    def purge_video(self, video_id: int) -> None:
        """彻底删除视频在库中的分析数据，不删除源媒体文件。"""
        with session_scope(self.session_factory) as session:
            video = session.get(VideoRow, video_id)
            if video is None:
                raise ValueError("video not found")
            global_person_ids = list(
                session.scalars(
                    select(GlobalObservationRow.global_person_id)
                    .where(
                        GlobalObservationRow.video_id == video_id,
                        GlobalObservationRow.global_person_id.is_not(None),
                    )
                    .distinct()
                ).all()
            )
            for model in (
                GlobalObservationRow,
                ReviewActionRow,
                PersonRow,
                SegmentRow,
                TrackRow,
                TrackDetectionRow,
                FaceCropRow,
            ):
                session.execute(delete(model).where(model.video_id == video_id))
            session.delete(video)
            for global_person_id in global_person_ids:
                _refresh_global_person_summary_orm(session, global_person_id)

    def list_people(self, video_id: int) -> list[dict[str, Any]]:
        """列出指定视频下的所有人物。"""
        stmt = select(PersonRow).where(PersonRow.video_id == video_id).order_by(PersonRow.person_id)
        with session_scope(self.session_factory) as session:
            rows = session.scalars(stmt).all()
        return [_model_payload(row) for row in rows]

    def list_segments(self, video_id: int, person_id: int | None = None) -> list[dict[str, Any]]:
        """列出指定视频的时间轴片段，可按人物过滤。"""
        stmt = select(SegmentRow).where(SegmentRow.video_id == video_id)
        if person_id is not None:
            stmt = stmt.where(SegmentRow.person_id == person_id)
        stmt = stmt.order_by(SegmentRow.start)
        with session_scope(self.session_factory) as session:
            rows = session.scalars(stmt).all()
        return [_model_payload(row) for row in rows]

    def list_tracks(self, video_id: int, person_id: int | None = None) -> list[dict[str, Any]]:
        """列出指定视频的人脸轨迹，可按人物过滤。"""
        stmt = select(TrackRow).where(TrackRow.video_id == video_id)
        if person_id is not None:
            stmt = stmt.where(TrackRow.person_id == person_id)
        stmt = stmt.order_by(TrackRow.start, TrackRow.track_id)
        with session_scope(self.session_factory) as session:
            rows = session.scalars(stmt).all()
        return [_model_payload(row) for row in rows]

    def list_track_detections(
        self,
        video_id: int,
        *,
        person_id: int | None = None,
        track_id: int | None = None,
        start: float | None = None,
        end: float | None = None,
        limit: int = 20000,
    ) -> list[dict[str, Any]]:
        """列出指定视频的逐帧人脸框，可按人物、轨迹或时间范围过滤。"""
        stmt = select(TrackDetectionRow).where(TrackDetectionRow.video_id == video_id)
        if person_id is not None:
            stmt = stmt.where(TrackDetectionRow.person_id == person_id)
        if track_id is not None:
            stmt = stmt.where(TrackDetectionRow.track_id == track_id)
        if start is not None:
            stmt = stmt.where(TrackDetectionRow.timestamp >= start)
        if end is not None:
            stmt = stmt.where(TrackDetectionRow.timestamp <= end)
        stmt = stmt.order_by(TrackDetectionRow.timestamp, TrackDetectionRow.track_id).limit(
            max(1, int(limit))
        )
        with session_scope(self.session_factory) as session:
            rows = session.scalars(stmt).all()
        return [_model_payload(row) for row in rows]

    def list_face_crops(self, video_id: int, person_id: int | None = None) -> list[dict[str, Any]]:
        """列出指定视频的人脸截图，可按人物过滤。"""
        stmt = select(FaceCropRow).where(FaceCropRow.video_id == video_id)
        if person_id is not None:
            stmt = stmt.where(FaceCropRow.person_id == person_id)
        stmt = stmt.order_by(FaceCropRow.person_id, FaceCropRow.track_id, FaceCropRow.id)
        with session_scope(self.session_factory) as session:
            rows = session.scalars(stmt).all()
            deduped_rows = _dedupe_face_crop_rows(rows)
            return _face_crop_payloads_with_bboxes(session, deduped_rows)

    def list_global_people(
        self,
        include_hidden: bool = False,
        *,
        include_deleted: bool = False,
        only_deleted: bool = False,
    ) -> list[dict[str, Any]]:
        """列出所有跨视频全局人物。"""
        profile_stmt = select(GlobalPersonRow)
        if only_deleted:
            profile_stmt = profile_stmt.where(GlobalPersonRow.deleted_at.is_not(None))
        elif not include_deleted:
            profile_stmt = profile_stmt.where(GlobalPersonRow.deleted_at.is_(None))
        profile_stmt = profile_stmt.order_by(GlobalPersonRow.global_person_id)

        filtered_obs_stmt = (
            select(GlobalObservationRow)
            .outerjoin(VideoRow, VideoRow.id == GlobalObservationRow.video_id)
            .where(or_(GlobalObservationRow.video_id.is_(None), VideoRow.deleted_at.is_(None)))
        )
        if not include_hidden:
            filtered_obs_stmt = filtered_obs_stmt.where(GlobalObservationRow.hidden == 0)

        with session_scope(self.session_factory) as session:
            profiles = session.scalars(profile_stmt).all()
            filtered_observations = session.scalars(filtered_obs_stmt).all()
            all_observation_counts = dict(
                session.execute(
                    select(
                        GlobalObservationRow.global_person_id,
                        func.count(GlobalObservationRow.id),
                    ).group_by(GlobalObservationRow.global_person_id)
                ).all()
            )
            asset_counts = dict(
                session.execute(
                    select(
                        FourViewAssetRow.global_person_id,
                        func.count(FourViewAssetRow.id),
                    ).group_by(FourViewAssetRow.global_person_id)
                ).all()
            )

        observations_by_profile: dict[str, list[GlobalObservationRow]] = {}
        for observation in filtered_observations:
            observations_by_profile.setdefault(observation.global_person_id, []).append(observation)

        rows: list[dict[str, Any]] = []
        for profile in profiles:
            observations = observations_by_profile.get(profile.global_person_id, [])
            if not observations and all_observation_counts.get(profile.global_person_id, 0) > 0:
                continue
            face = next(
                (
                    item
                    for item in sorted(observations, key=lambda item: (-item.confirmed, item.id))
                    if item.representative_face_path is not None
                ),
                None,
            )
            observation_labels = [item.label for item in observations if item.label]
            rows.append(
                {
                    "global_person_id": profile.global_person_id,
                    "label": (
                        profile.label
                        or (max(observation_labels) if observation_labels else None)
                        or profile.global_person_id
                    ),
                    "representative_face_path": (
                        face.representative_face_path
                        if face is not None
                        else profile.representative_face_path
                    ),
                    "representative_timestamp": (
                        face.representative_timestamp
                        if face is not None
                        else profile.representative_timestamp
                    ),
                    "representative_frame_index": (
                        face.representative_frame_index
                        if face is not None
                        else profile.representative_frame_index
                    ),
                    "observation_count": len(observations),
                    "confirmed_count": sum(int(item.confirmed) for item in observations),
                    "total_duration": sum(float(item.total_duration) for item in observations),
                    "deleted_at": profile.deleted_at,
                    "four_view_asset_count": int(asset_counts.get(profile.global_person_id, 0)),
                }
            )
        return rows

    def list_global_observations(
        self,
        global_person_id: str | None = None,
        include_hidden: bool = False,
    ) -> list[dict[str, Any]]:
        """列出跨视频观测记录，可按全局人物 ID 过滤。"""
        stmt = (
            select(GlobalObservationRow, VideoRow)
            .outerjoin(VideoRow, VideoRow.id == GlobalObservationRow.video_id)
            .where(or_(GlobalObservationRow.video_id.is_(None), VideoRow.deleted_at.is_(None)))
        )
        if global_person_id is not None:
            stmt = stmt.where(GlobalObservationRow.global_person_id == global_person_id)
        if not include_hidden:
            stmt = stmt.where(GlobalObservationRow.hidden == 0)
        stmt = stmt.order_by(
            GlobalObservationRow.global_person_id,
            GlobalObservationRow.video_path,
            GlobalObservationRow.local_person_id,
        )
        with session_scope(self.session_factory) as session:
            rows = session.execute(stmt).all()
        payloads: list[dict[str, Any]] = []
        for observation, video in rows:
            payload = _model_payload(observation)
            payload["video_title"] = video.title if video is not None else None
            payload["series_name"] = video.series_name if video is not None else None
            payload["original_filename"] = video.original_filename if video is not None else None
            payload["source_path"] = video.source_path if video is not None else None
            payload["source_directory"] = video.source_directory if video is not None else None
            payloads.append(payload)
        return payloads

    def search_people(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        """搜索本地人物和跨视频人物观测。"""
        keyword = query.strip()
        limit = max(1, min(int(limit), 200))
        like = f"%{keyword}%"
        stmt = (
            select(PersonRow, VideoRow, GlobalPersonRow)
            .join(VideoRow, VideoRow.id == PersonRow.video_id)
            .outerjoin(GlobalPersonRow, GlobalPersonRow.global_person_id == PersonRow.global_person_id)
            .where(PersonRow.hidden == 0, VideoRow.deleted_at.is_(None))
        )
        if keyword:
            stmt = stmt.where(
                or_(
                    PersonRow.label.like(like),
                    PersonRow.global_person_id.like(like),
                    VideoRow.title.like(like),
                    VideoRow.series_name.like(like),
                    VideoRow.source_path.like(like),
                    VideoRow.source_directory.like(like),
                    VideoRow.path.like(like),
                )
            )
        stmt = stmt.order_by(
            case((PersonRow.label == keyword, 0), else_=1),
            PersonRow.detection_count.desc(),
            PersonRow.total_duration.desc(),
            VideoRow.id.desc(),
        ).limit(limit)
        with session_scope(self.session_factory) as session:
            rows = session.execute(stmt).all()
        payloads: list[dict[str, Any]] = []
        for person, video, global_person in rows:
            payloads.append(
                {
                    "id": person.id,
                    "video_id": person.video_id,
                    "person_id": person.person_id,
                    "label": person.label,
                    "global_person_id": person.global_person_id,
                    "appearances": person.appearances,
                    "total_duration": person.total_duration,
                    "detection_count": person.detection_count,
                    "representative_face_path": person.representative_face_path,
                    "video_title": video.title,
                    "video_path": video.path,
                    "series_name": video.series_name,
                    "source_path": video.source_path,
                    "source_directory": video.source_directory,
                    "duration_seconds": video.duration_seconds,
                    "global_label": global_person.label if global_person is not None else None,
                    "observation_count": (
                        global_person.observation_count if global_person is not None else None
                    ),
                    "confirmed_count": (
                        global_person.confirmed_count if global_person is not None else None
                    ),
                }
            )
        return payloads

    def save_analyze_job(self, payload: dict[str, Any]) -> None:
        """保存分析任务状态快照，供远程轮询和历史查询使用。"""
        job_id = str(payload["job_id"])
        status = str(payload.get("status", "queued"))
        stage = str(payload.get("stage", "queued"))
        progress = float(payload.get("progress", 0.0))
        message = str(payload.get("message", ""))
        payload_json = json.dumps(payload, ensure_ascii=False)
        timestamp = _database_timestamp()
        with session_scope(self.session_factory) as session:
            row = session.get(AnalyzeJobRow, job_id)
            if row is None:
                session.add(
                    AnalyzeJobRow(
                        job_id=job_id,
                        status=status,
                        stage=stage,
                        progress=progress,
                        message=message,
                        payload_json=payload_json,
                        created_at=timestamp,
                        updated_at=timestamp,
                    )
                )
                return
            row.status = status
            row.stage = stage
            row.progress = progress
            row.message = message
            row.payload_json = payload_json
            row.updated_at = timestamp

    def get_analyze_job(self, job_id: str) -> dict[str, Any] | None:
        """读取持久化的分析任务状态快照。"""
        with session_scope(self.session_factory) as session:
            row = session.get(AnalyzeJobRow, job_id)
            return _analyze_job_payload(row) if row is not None else None

    def list_analyze_jobs(self, limit: int = 10) -> list[dict[str, Any]]:
        """按更新时间倒序读取最近的分析任务状态快照。"""
        safe_limit = max(1, min(int(limit), 50))
        stmt = (
            select(AnalyzeJobRow)
            .order_by(AnalyzeJobRow.updated_at.desc(), AnalyzeJobRow.created_at.desc())
            .limit(safe_limit)
        )
        with session_scope(self.session_factory) as session:
            rows = session.scalars(stmt).all()
        return [_analyze_job_payload(row) for row in rows]

    def confirm_global_observation(
        self,
        global_person_id: str,
        video_path: str,
        local_person_id: int,
    ) -> None:
        """确认某个观测属于指定全局人物。"""
        with session_scope(self.session_factory) as session:
            row = _require_global_observation_orm(
                session,
                global_person_id,
                video_path,
                local_person_id,
            )
            row.confirmed = 1
            row.rejected = 0
            video = session.scalars(select(VideoRow).where(VideoRow.path == video_path)).first()
            if video is not None:
                for person in session.scalars(
                    select(PersonRow).where(
                        PersonRow.person_id == local_person_id,
                        PersonRow.video_id == video.id,
                    )
                ).all():
                    person.global_person_id = global_person_id
            _refresh_global_person_summary_orm(session, global_person_id)

    def reject_global_observation(
        self,
        global_person_id: str,
        video_path: str,
        local_person_id: int,
        new_global_person_id: str,
    ) -> None:
        """拒绝某个观测与原全局人物的关联，并将其归入新全局人物。"""
        with session_scope(self.session_factory) as session:
            row = _require_global_observation_orm(
                session,
                global_person_id,
                video_path,
                local_person_id,
            )
            row.global_person_id = new_global_person_id
            row.confirmed = 1
            row.rejected = 0
            video = session.scalars(select(VideoRow).where(VideoRow.path == video_path)).first()
            if video is not None:
                for person in session.scalars(
                    select(PersonRow).where(
                        PersonRow.person_id == local_person_id,
                        PersonRow.video_id == video.id,
                    )
                ).all():
                    person.global_person_id = new_global_person_id
            _refresh_global_person_summary_orm(session, global_person_id)
            _refresh_global_person_summary_orm(session, new_global_person_id)

    def link_person_to_global(
        self,
        video_id: int,
        local_person_id: int,
        global_person_id: str,
    ) -> None:
        """将某集里的本地人物关联到指定人物档案。"""
        next_global_person_id = global_person_id.strip()
        if not next_global_person_id:
            raise ValueError("global_person_id must not be empty")
        with session_scope(self.session_factory) as session:
            person = _require_person_orm(session, video_id, local_person_id)
            video = session.get(VideoRow, video_id)
            if video is None:
                raise ValueError("video not found")
            previous_global_person_id = person.global_person_id
            if previous_global_person_id and previous_global_person_id != next_global_person_id:
                session.execute(
                    delete(GlobalObservationRow).where(
                        GlobalObservationRow.global_person_id == previous_global_person_id,
                        GlobalObservationRow.local_person_id == local_person_id,
                        or_(
                            GlobalObservationRow.video_id == video_id,
                            GlobalObservationRow.video_path == video.path,
                        ),
                    )
                )
                _refresh_global_person_summary_orm(session, previous_global_person_id)

            person.global_person_id = next_global_person_id
            _upsert_global_person_from_summary_orm(
                session,
                video_id,
                video.path,
                {
                    "person_id": local_person_id,
                    "label": person.label,
                    "global_person_id": next_global_person_id,
                    "appearances": person.appearances,
                    "total_duration": person.total_duration,
                    "detection_count": person.detection_count,
                    "representative_face_path": person.representative_face_path,
                    "representative_timestamp": person.representative_timestamp,
                    "representative_frame_index": person.representative_frame_index,
                    "hidden": person.hidden,
                },
            )
            observation = session.scalars(
                select(GlobalObservationRow).where(
                    GlobalObservationRow.global_person_id == next_global_person_id,
                    GlobalObservationRow.video_id == video_id,
                    GlobalObservationRow.local_person_id == local_person_id,
                )
            ).first()
            if observation is not None:
                observation.confirmed = 1
                observation.rejected = 0
            _refresh_global_person_summary_orm(session, next_global_person_id)
            _record_review_action_orm(
                session,
                video_id=video_id,
                action="link_global_person",
                payload={
                    "person_id": local_person_id,
                    "global_person_id": next_global_person_id,
                },
            )

    def create_manual_global_person(self, label: str | None = None) -> str:
        """手动创建空白人物档案，不依赖任何视频观测。"""
        next_label = label.strip() if label is not None and label.strip() else "未命名人物"
        global_person_id = _manual_global_person_id()
        with session_scope(self.session_factory) as session:
            session.add(
                GlobalPersonRow(
                    global_person_id=global_person_id,
                    label=next_label,
                    representative_face_path=None,
                    representative_timestamp=None,
                    representative_frame_index=None,
                    observation_count=0,
                    confirmed_count=0,
                    total_duration=0.0,
                    deleted_at=None,
                )
            )
            _record_global_person_action_orm(
                session,
                global_person_id,
                "create_manual_profile",
                {"label": next_label},
            )
        return global_person_id

    def rename_global_person(self, global_person_id: str, label: str) -> None:
        """重命名人物档案的全局展示名称。"""
        target_id = global_person_id.strip()
        clean_label = label.strip()
        if not target_id:
            raise ValueError("global_person_id must not be empty")
        if not clean_label:
            raise ValueError("label must not be empty")
        with session_scope(self.session_factory) as session:
            row = session.get(GlobalPersonRow, target_id)
            if row is None:
                raise ValueError(f"global person not found: {target_id}")
            row.label = clean_label
            _record_global_person_action_orm(
                session,
                target_id,
                "rename_profile",
                {"label": clean_label},
            )

    def delete_global_person(self, global_person_id: str) -> None:
        """把人物档案移入回收站，保留本地关联和档案资产。"""
        target_id = global_person_id.strip()
        if not target_id:
            raise ValueError("global_person_id must not be empty")
        deleted_at = datetime.now(UTC).isoformat()
        with session_scope(self.session_factory) as session:
            row = session.get(GlobalPersonRow, target_id)
            if row is None:
                raise ValueError(f"global person not found: {target_id}")
            row.deleted_at = deleted_at
            _record_global_person_action_orm(
                session,
                target_id,
                "trash_profile",
                {"deleted_at": deleted_at},
            )

    def restore_global_person(self, global_person_id: str) -> None:
        """从人物档案回收站恢复档案。"""
        target_id = global_person_id.strip()
        if not target_id:
            raise ValueError("global_person_id must not be empty")
        with session_scope(self.session_factory) as session:
            row = session.get(GlobalPersonRow, target_id)
            if row is None:
                raise ValueError(f"global person not found: {target_id}")
            row.deleted_at = None
            _record_global_person_action_orm(session, target_id, "restore_profile", {})

    def purge_global_person(self, global_person_id: str) -> None:
        """彻底删除人物档案，并解除本地人物对该档案的关联。"""
        target_id = global_person_id.strip()
        if not target_id:
            raise ValueError("global_person_id must not be empty")
        with session_scope(self.session_factory) as session:
            row = session.get(GlobalPersonRow, target_id)
            if row is None:
                raise ValueError(f"global person not found: {target_id}")
            _record_global_person_action_orm(session, target_id, "purge_profile", {})
            people = session.scalars(
                select(PersonRow).where(PersonRow.global_person_id == target_id)
            ).all()
            for person in people:
                person.global_person_id = None
            session.execute(
                delete(FourViewAssetRow).where(FourViewAssetRow.global_person_id == target_id)
            )
            session.execute(
                delete(GlobalObservationRow).where(
                    GlobalObservationRow.global_person_id == target_id
                )
            )
            session.delete(row)

    def merge_global_people(self, source_global_person_id: str, target_global_person_id: str) -> None:
        """将源人物档案合并到目标人物档案，保留目标 ID。"""
        source_id = source_global_person_id.strip()
        target_id = target_global_person_id.strip()
        if not source_id or not target_id:
            raise ValueError("global_person_id must not be empty")
        if source_id == target_id:
            raise ValueError("source and target global person must be different")
        with session_scope(self.session_factory) as session:
            source = session.get(GlobalPersonRow, source_id)
            target = session.get(GlobalPersonRow, target_id)
            if source is None:
                raise ValueError(f"global person not found: {source_id}")
            if target is None:
                raise ValueError(f"global person not found: {target_id}")
            target_had_face = target.representative_face_path is not None

            source_observations = session.scalars(
                select(GlobalObservationRow)
                .where(GlobalObservationRow.global_person_id == source_id)
                .order_by(GlobalObservationRow.id)
            ).all()
            for observation in source_observations:
                existing = session.scalars(
                    select(GlobalObservationRow).where(
                        GlobalObservationRow.global_person_id == target_id,
                        GlobalObservationRow.video_path == observation.video_path,
                        GlobalObservationRow.local_person_id == observation.local_person_id,
                    )
                ).first()
                if existing is None:
                    observation.global_person_id = target_id
                    continue
                existing.video_id = existing.video_id or observation.video_id
                existing.label = existing.label or observation.label
                existing.representative_face_path = (
                    existing.representative_face_path or observation.representative_face_path
                )
                existing.representative_timestamp = (
                    existing.representative_timestamp or observation.representative_timestamp
                )
                existing.representative_frame_index = (
                    existing.representative_frame_index or observation.representative_frame_index
                )
                existing.appearances = max(existing.appearances, observation.appearances)
                existing.total_duration = max(existing.total_duration, observation.total_duration)
                existing.detection_count = max(existing.detection_count, observation.detection_count)
                existing.confirmed = max(existing.confirmed, observation.confirmed)
                existing.rejected = min(existing.rejected, observation.rejected)
                existing.hidden = min(existing.hidden, observation.hidden)
                session.delete(observation)

            for person in session.scalars(
                select(PersonRow).where(PersonRow.global_person_id == source_id)
            ).all():
                person.global_person_id = target_id
            for asset in session.scalars(
                select(FourViewAssetRow).where(FourViewAssetRow.global_person_id == source_id)
            ).all():
                asset.global_person_id = target_id

            target.label = target.label or source.label
            target.deleted_at = None
            target.representative_face_path = (
                target.representative_face_path or source.representative_face_path
            )
            target.representative_timestamp = (
                target.representative_timestamp or source.representative_timestamp
            )
            target.representative_frame_index = (
                target.representative_frame_index or source.representative_frame_index
            )
            session.delete(source)
            session.flush()
            _refresh_global_person_summary_orm(session, target_id)
            _record_global_person_action_orm(
                session,
                target_id,
                "merge_profile",
                {"source_global_person_id": source_id},
            )
            if not target_had_face and source.representative_face_path is not None:
                target.representative_face_path = (
                    target.representative_face_path or source.representative_face_path
                )
                target.representative_timestamp = (
                    target.representative_timestamp or source.representative_timestamp
                )
                target.representative_frame_index = (
                    target.representative_frame_index or source.representative_frame_index
                )

    def list_global_person_actions(
        self,
        global_person_id: str | None = None,
        *,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """读取人物档案操作历史，可按档案过滤。"""
        safe_limit = max(1, min(int(limit), 200))
        stmt = select(GlobalPersonActionRow)
        if global_person_id is not None:
            stmt = stmt.where(GlobalPersonActionRow.global_person_id == global_person_id.strip())
        stmt = stmt.order_by(GlobalPersonActionRow.id.desc()).limit(safe_limit)
        with session_scope(self.session_factory) as session:
            rows = session.scalars(stmt).all()
        actions = []
        for row in rows:
            item = _model_payload(row)
            item["payload"] = json.loads(item.pop("payload_json"))
            actions.append(item)
        return actions

    def create_global_person_from_local(
        self,
        video_id: int,
        local_person_id: int,
        label: str | None = None,
    ) -> str:
        """从当前视频人物直接新建人物档案并完成关联。"""
        with session_scope(self.session_factory) as session:
            person = _require_person_orm(session, video_id, local_person_id)
            video = session.get(VideoRow, video_id)
            if video is None:
                raise ValueError("video not found")
            if video.deleted_at is not None:
                raise ValueError("video not found")
            previous_global_person_id = person.global_person_id
            if previous_global_person_id:
                session.execute(
                    delete(GlobalObservationRow).where(
                        GlobalObservationRow.global_person_id == previous_global_person_id,
                        GlobalObservationRow.local_person_id == local_person_id,
                        or_(
                            GlobalObservationRow.video_id == video_id,
                            GlobalObservationRow.video_path == video.path,
                        ),
                    )
                )
                _refresh_global_person_summary_orm(session, previous_global_person_id)

            global_person_id = _manual_global_person_id()
            next_label = label.strip() if label is not None and label.strip() else person.label
            person.global_person_id = global_person_id
            _upsert_global_person_from_summary_orm(
                session,
                video_id,
                video.path,
                {
                    "person_id": local_person_id,
                    "label": next_label,
                    "global_person_id": global_person_id,
                    "appearances": person.appearances,
                    "total_duration": person.total_duration,
                    "detection_count": person.detection_count,
                    "representative_face_path": person.representative_face_path,
                    "representative_timestamp": person.representative_timestamp,
                    "representative_frame_index": person.representative_frame_index,
                    "hidden": person.hidden,
                },
            )
            observation = session.scalars(
                select(GlobalObservationRow).where(
                    GlobalObservationRow.global_person_id == global_person_id,
                    GlobalObservationRow.video_id == video_id,
                    GlobalObservationRow.local_person_id == local_person_id,
                )
            ).first()
            if observation is not None:
                observation.confirmed = 1
                observation.rejected = 0
                observation.label = next_label
            _refresh_global_person_summary_orm(session, global_person_id)
            _record_review_action_orm(
                session,
                video_id=video_id,
                action="create_global_person",
                payload={
                    "person_id": local_person_id,
                    "global_person_id": global_person_id,
                    "label": next_label,
                },
            )
        return global_person_id

    def list_four_view_assets(self, global_person_id: str) -> list[dict[str, Any]]:
        """列出某个人物档案下的四视图原图资产。"""
        stmt = (
            select(FourViewAssetRow)
            .where(FourViewAssetRow.global_person_id == global_person_id)
            .order_by(FourViewAssetRow.id.desc())
        )
        with session_scope(self.session_factory) as session:
            if session.get(GlobalPersonRow, global_person_id) is None:
                raise ValueError(f"global person not found: {global_person_id}")
            rows = session.scalars(stmt).all()
        return [_model_payload(row) for row in rows]

    def add_four_view_asset(
        self,
        global_person_id: str,
        *,
        image_path: str,
        label: str | None = None,
        reference_count: int = 0,
    ) -> dict[str, Any]:
        """给人物档案登记一张未切分的四视图原图。"""
        clean_label = label.strip() if label is not None and label.strip() else "四视图原图"
        clean_path = image_path.strip()
        if not clean_path:
            raise ValueError("image_path must not be empty")
        with session_scope(self.session_factory) as session:
            profile = session.get(GlobalPersonRow, global_person_id)
            if profile is None:
                raise ValueError(f"global person not found: {global_person_id}")
            row = FourViewAssetRow(
                global_person_id=global_person_id,
                label=clean_label,
                image_path=clean_path,
                reference_count=max(0, int(reference_count)),
            )
            session.add(row)
            if profile.representative_face_path is None:
                profile.representative_face_path = clean_path
            session.flush()
            return _model_payload(row)

    def delete_four_view_asset(self, global_person_id: str, asset_id: int) -> dict[str, Any]:
        """删除人物档案下的一张四视图原图资产。"""
        with session_scope(self.session_factory) as session:
            profile = session.get(GlobalPersonRow, global_person_id)
            if profile is None:
                raise ValueError(f"global person not found: {global_person_id}")
            row = session.get(FourViewAssetRow, asset_id)
            if row is None or row.global_person_id != global_person_id:
                raise ValueError(f"four view asset not found: {asset_id}")
            payload = _model_payload(row)
            deleted_path = row.image_path
            session.delete(row)
            session.flush()
            if profile.representative_face_path == deleted_path:
                replacement = session.scalars(
                    select(FourViewAssetRow)
                    .where(FourViewAssetRow.global_person_id == global_person_id)
                    .order_by(FourViewAssetRow.id.desc())
                    .limit(1)
                ).first()
                profile.representative_face_path = (
                    replacement.image_path if replacement is not None else None
                )
                _refresh_global_person_summary_orm(session, global_person_id)
            _record_global_person_action_orm(
                session,
                global_person_id,
                "delete_four_view_asset",
                {
                    "asset_id": int(asset_id),
                    "image_path": deleted_path,
                },
            )
            return payload

    def move_four_view_assets(
        self,
        source_global_person_id: str,
        target_global_person_id: str,
    ) -> dict[str, Any]:
        """把四视图资产从一个人物档案迁移到另一个人物档案。"""
        source_id = source_global_person_id.strip()
        target_id = target_global_person_id.strip()
        if not source_id or not target_id:
            raise ValueError("global_person_id must not be empty")
        if source_id == target_id:
            raise ValueError("source and target global person must be different")
        with session_scope(self.session_factory) as session:
            source = session.get(GlobalPersonRow, source_id)
            target = session.get(GlobalPersonRow, target_id)
            if source is None:
                raise ValueError(f"global person not found: {source_id}")
            if target is None:
                raise ValueError(f"global person not found: {target_id}")
            rows = session.scalars(
                select(FourViewAssetRow)
                .where(FourViewAssetRow.global_person_id == source_id)
                .order_by(FourViewAssetRow.id.desc())
            ).all()
            moved_paths = {row.image_path for row in rows}
            for row in rows:
                row.global_person_id = target_id
            session.flush()
            if rows and target.representative_face_path is None:
                target.representative_face_path = rows[0].image_path
            if source.representative_face_path in moved_paths:
                replacement = session.scalars(
                    select(FourViewAssetRow)
                    .where(FourViewAssetRow.global_person_id == source_id)
                    .order_by(FourViewAssetRow.id.desc())
                    .limit(1)
                ).first()
                source.representative_face_path = (
                    replacement.image_path if replacement is not None else None
                )
            moved_payloads = [_model_payload(row) for row in rows]
            _record_global_person_action_orm(
                session,
                source_id,
                "move_four_view_assets_out",
                {
                    "target_global_person_id": target_id,
                    "asset_ids": [int(row.id) for row in rows],
                },
            )
            _record_global_person_action_orm(
                session,
                target_id,
                "move_four_view_assets_in",
                {
                    "source_global_person_id": source_id,
                    "asset_ids": [int(row.id) for row in rows],
                },
            )
            source_assets = session.scalars(
                select(FourViewAssetRow)
                .where(FourViewAssetRow.global_person_id == source_id)
                .order_by(FourViewAssetRow.id.desc())
            ).all()
            target_assets = session.scalars(
                select(FourViewAssetRow)
                .where(FourViewAssetRow.global_person_id == target_id)
                .order_by(FourViewAssetRow.id.desc())
            ).all()
            return {
                "moved_assets": moved_payloads,
                "source_four_view_assets": [_model_payload(row) for row in source_assets],
                "target_four_view_assets": [_model_payload(row) for row in target_assets],
            }

    def rename_person(self, video_id: int, person_id: int, label: str) -> None:
        """重命名指定视频中的人物。"""
        if not label.strip():
            raise ValueError("label must not be empty")
        with session_scope(self.session_factory) as session:
            person = _require_person_orm(session, video_id, person_id)
            person.label = label.strip()
            _record_review_action_orm(
                session,
                video_id=video_id,
                action="rename_person",
                payload={"person_id": person_id, "label": label.strip()},
            )

    def set_person_hidden(self, video_id: int, person_id: int, hidden: bool) -> None:
        """设置指定视频人物是否在默认视图中隐藏。"""
        with session_scope(self.session_factory) as session:
            person = _require_person_orm(session, video_id, person_id)
            video = session.get(VideoRow, video_id)
            if video is None:
                raise ValueError("video not found")
            hidden_value = 1 if hidden else 0
            person.hidden = hidden_value
            observations = session.scalars(
                select(GlobalObservationRow).where(
                    GlobalObservationRow.local_person_id == person_id,
                    or_(
                        GlobalObservationRow.video_id == video_id,
                        GlobalObservationRow.video_path == video.path,
                    ),
                )
            ).all()
            for observation in observations:
                observation.hidden = hidden_value
            if person.global_person_id:
                _refresh_global_person_summary_orm(session, person.global_person_id)
            _refresh_video_people_count_orm(session, video_id)
            _record_review_action_orm(
                session,
                video_id=video_id,
                action="hide_person" if hidden else "show_person",
                payload={"person_id": person_id, "hidden": hidden},
            )

    def delete_person(self, video_id: int, person_id: int) -> None:
        """删除指定视频中的人物及其关联片段、轨迹和截图。"""
        with session_scope(self.session_factory) as session:
            person = _require_person_orm(session, video_id, person_id)
            previous_global_person_id = person.global_person_id
            session.delete(person)
            for model in (SegmentRow, TrackRow, TrackDetectionRow, FaceCropRow):
                session.execute(
                    delete(model).where(model.video_id == video_id, model.person_id == person_id)
                )
            if previous_global_person_id:
                session.execute(
                    delete(GlobalObservationRow).where(
                        GlobalObservationRow.global_person_id == previous_global_person_id,
                        GlobalObservationRow.local_person_id == person_id,
                        GlobalObservationRow.video_id == video_id,
                    )
                )
                _refresh_global_person_summary_orm(session, previous_global_person_id)
            _refresh_video_people_count_orm(session, video_id)
            _record_review_action_orm(
                session,
                video_id=video_id,
                action="delete_person",
                payload={"person_id": person_id},
            )

    def merge_people(self, video_id: int, source_person_id: int, target_person_id: int) -> None:
        """将源人物合并到目标人物。"""
        if source_person_id == target_person_id:
            raise ValueError("source and target person must be different")
        with session_scope(self.session_factory) as session:
            source = _require_person_orm(session, video_id, source_person_id)
            target = _require_person_orm(session, video_id, target_person_id)
            fallback = _model_payload(target)
            for model in (SegmentRow, TrackRow, TrackDetectionRow, FaceCropRow):
                for row in session.scalars(
                    select(model).where(model.video_id == video_id, model.person_id == source_person_id)
                ).all():
                    row.person_id = target_person_id
            session.delete(source)
            _recompute_person_summary_orm(session, video_id, target_person_id, fallback=fallback)
            _refresh_video_people_count_orm(session, video_id)
            _record_review_action_orm(
                session,
                video_id=video_id,
                action="merge_people",
                payload={
                    "source_person_id": source_person_id,
                    "target_person_id": target_person_id,
                },
            )

    def assign_tracks_to_person(
        self,
        video_id: int,
        track_ids: list[int],
        target_person_id: int,
    ) -> None:
        """将一批轨迹统一归类到目标人物。"""
        if not track_ids:
            raise ValueError("track_ids must not be empty")
        unique_track_ids = sorted(set(track_ids))
        with session_scope(self.session_factory) as session:
            target = _require_person_orm(session, video_id, target_person_id)
            fallback = _model_payload(target)
            rows = session.scalars(
                select(TrackRow).where(
                    TrackRow.video_id == video_id,
                    TrackRow.track_id.in_(unique_track_ids),
                )
            ).all()
            found = {int(row.track_id) for row in rows}
            missing = sorted(set(unique_track_ids) - found)
            if missing:
                raise ValueError(f"tracks not found: {missing}")

            affected_person_ids = {
                int(row.person_id)
                for row in rows
                if row.person_id is not None and int(row.person_id) != target_person_id
            }
            for row in rows:
                row.person_id = target_person_id
            for model in (FaceCropRow, TrackDetectionRow):
                for row in session.scalars(
                    select(model).where(
                        model.video_id == video_id,
                        model.track_id.in_(unique_track_ids),
                    )
                ).all():
                    row.person_id = target_person_id
            for person_id in sorted(affected_person_ids | {target_person_id}):
                _reassign_segments_from_tracks_orm(session, video_id, person_id)
            for person_id in sorted(affected_person_ids):
                _delete_empty_person_orm(session, video_id, person_id)
            _recompute_person_summary_orm(session, video_id, target_person_id, fallback=fallback)
            _refresh_video_people_count_orm(session, video_id)
            _record_review_action_orm(
                session,
                video_id=video_id,
                action="assign_tracks",
                payload={
                    "track_ids": unique_track_ids,
                    "target_person_id": target_person_id,
                    "source_person_ids": sorted(affected_person_ids),
                },
            )

    def delete_tracks(self, video_id: int, track_ids: list[int]) -> None:
        """删除指定轨迹，并重建受影响人物的片段。"""
        if not track_ids:
            raise ValueError("track_ids must not be empty")
        unique_track_ids = sorted(set(track_ids))
        with session_scope(self.session_factory) as session:
            rows = session.scalars(
                select(TrackRow).where(
                    TrackRow.video_id == video_id,
                    TrackRow.track_id.in_(unique_track_ids),
                )
            ).all()
            found = {int(row.track_id) for row in rows}
            missing = sorted(set(unique_track_ids) - found)
            if missing:
                raise ValueError(f"tracks not found: {missing}")
            affected_person_ids = {
                int(row.person_id)
                for row in rows
                if row.person_id is not None
            }
            for model in (TrackRow, TrackDetectionRow, FaceCropRow):
                session.execute(
                    delete(model).where(
                        model.video_id == video_id,
                        model.track_id.in_(unique_track_ids),
                    )
                )
            for person_id in sorted(affected_person_ids):
                _reassign_segments_from_tracks_orm(session, video_id, person_id)
                _delete_empty_person_orm(session, video_id, person_id)
            _refresh_video_people_count_orm(session, video_id)
            _record_review_action_orm(
                session,
                video_id=video_id,
                action="delete_tracks",
                payload={"track_ids": unique_track_ids, "person_ids": sorted(affected_person_ids)},
            )

    def split_tracks_to_person(
        self,
        video_id: int,
        source_person_id: int,
        track_ids: list[int],
        label: str | None = None,
    ) -> int:
        """将源人物中的指定轨迹拆分为一个新人物。"""
        if not track_ids:
            raise ValueError("track_ids must not be empty")
        unique_track_ids = sorted(set(track_ids))
        with session_scope(self.session_factory) as session:
            source = _require_person_orm(session, video_id, source_person_id)
            source_fallback = _model_payload(source)
            rows = session.scalars(
                select(TrackRow).where(
                    TrackRow.video_id == video_id,
                    TrackRow.person_id == source_person_id,
                    TrackRow.track_id.in_(unique_track_ids),
                )
            ).all()
            found = {int(row.track_id) for row in rows}
            missing = sorted(set(unique_track_ids) - found)
            if missing:
                raise ValueError(f"tracks do not belong to source person: {missing}")

            new_person_id = _next_local_person_id_orm(session, video_id)
            next_label = (
                label.strip() if label and label.strip() else f"person_{new_person_id + 1:03d}"
            )
            session.add(
                PersonRow(
                    video_id=video_id,
                    person_id=new_person_id,
                    label=next_label,
                    global_person_id=None,
                    appearances=0,
                    total_duration=0.0,
                    detection_count=0,
                    representative_face_path=None,
                    representative_timestamp=None,
                    representative_frame_index=None,
                    hidden=0,
                )
            )
            for row in rows:
                row.person_id = new_person_id
            for model in (FaceCropRow, TrackDetectionRow):
                for row in session.scalars(
                    select(model).where(
                        model.video_id == video_id,
                        model.person_id == source_person_id,
                        model.track_id.in_(unique_track_ids),
                    )
                ).all():
                    row.person_id = new_person_id
            _reassign_segments_from_tracks_orm(session, video_id, source_person_id)
            _reassign_segments_from_tracks_orm(session, video_id, new_person_id)
            _recompute_person_summary_orm(
                session,
                video_id,
                source_person_id,
                fallback=source_fallback,
            )
            _recompute_person_summary_orm(session, video_id, new_person_id)
            _refresh_video_people_count_orm(session, video_id)
            _record_review_action_orm(
                session,
                video_id=video_id,
                action="split_tracks",
                payload={
                    "source_person_id": source_person_id,
                    "new_person_id": new_person_id,
                    "track_ids": unique_track_ids,
                },
            )
        return new_person_id

    def import_timeline(
        self,
        timeline_path: Path,
        *,
        display_title: str | None = None,
        series_name: str | None = None,
        original_filename: str | None = None,
        source_path: str | None = None,
        source_directory: str | None = None,
    ) -> int:
        """将 timeline.json 导入数据库，返回视频 ID。"""
        payload = json.loads(timeline_path.read_text(encoding="utf-8"))
        video = payload["video"]
        diagnostics = payload.get("diagnostics") or {}
        video_path = video["path"]
        duration = video["frame_count"] / video["fps"] if video.get("fps", 0) else 0.0

        with session_scope(self.session_factory) as session:
            existing_video = session.scalars(
                select(VideoRow).where(VideoRow.path == video_path)
            ).first()
            next_source_path = _first_non_empty(
                source_path,
                video.get("source_path"),
                existing_video.source_path if existing_video is not None else None,
                video_path,
            )
            next_source_directory = _first_non_empty(
                source_directory,
                video.get("source_directory"),
                existing_video.source_directory if existing_video is not None else None,
                str(Path(next_source_path).parent),
            )
            next_original_filename = (
                original_filename.strip()
                if original_filename is not None and original_filename.strip()
                else _first_non_empty(
                    existing_video.original_filename if existing_video is not None else None,
                    video.get("original_filename"),
                    Path(next_source_path).name,
                )
            )
            next_title = _video_display_title(
                video_path=video_path,
                display_title=display_title,
                original_filename=next_original_filename,
                existing_title=existing_video.title if existing_video is not None else None,
                payload_title=video.get("title"),
            )
            next_series_name = (
                series_name.strip()
                if series_name is not None
                else (existing_video.series_name if existing_video is not None else "")
            )
            if existing_video is None:
                existing_video = VideoRow(
                    path=video_path,
                    title=next_title,
                    fps=float(video["fps"]),
                    frame_count=int(video["frame_count"]),
                    width=int(video["width"]),
                    height=int(video["height"]),
                    duration_seconds=float(duration),
                    people_count=int(payload.get("people_count", 0)),
                    timeline_path=str(timeline_path),
                    diagnostics_json=json.dumps(diagnostics, ensure_ascii=False),
                    original_filename=next_original_filename,
                    series_name=next_series_name,
                    source_path=next_source_path,
                    source_directory=next_source_directory,
                    deleted_at=None,
                )
                session.add(existing_video)
                session.flush()
            else:
                existing_video.title = next_title
                existing_video.fps = float(video["fps"])
                existing_video.frame_count = int(video["frame_count"])
                existing_video.width = int(video["width"])
                existing_video.height = int(video["height"])
                existing_video.duration_seconds = float(duration)
                existing_video.people_count = int(payload.get("people_count", 0))
                existing_video.timeline_path = str(timeline_path)
                existing_video.diagnostics_json = json.dumps(diagnostics, ensure_ascii=False)
                existing_video.original_filename = next_original_filename
                existing_video.series_name = next_series_name
                existing_video.source_path = next_source_path
                existing_video.source_directory = next_source_directory
                existing_video.deleted_at = None
                session.flush()

            video_id = int(existing_video.id)
            # 清空该视频旧数据后重新导入
            for model in (PersonRow, SegmentRow, TrackRow, TrackDetectionRow, FaceCropRow):
                session.execute(delete(model).where(model.video_id == video_id))

            face_crop_rows: list[FaceCropRow] = []
            for person in payload.get("people", []):
                session.add(
                    PersonRow(
                        video_id=video_id,
                        person_id=int(person["person_id"]),
                        label=str(person["label"]),
                        global_person_id=person.get("global_person_id"),
                        appearances=int(person.get("appearances", 0)),
                        total_duration=float(person.get("total_duration", 0.0)),
                        detection_count=int(person.get("detection_count", 0)),
                        representative_face_path=person.get("representative_face_path"),
                        representative_timestamp=person.get("representative_timestamp"),
                        representative_frame_index=person.get("representative_frame_index"),
                        hidden=int(person.get("hidden", 0) or 0),
                    )
                )
                if person.get("representative_face_path"):
                    face_crop_rows.append(
                        FaceCropRow(
                            video_id=video_id,
                            person_id=int(person["person_id"]),
                            track_id=None,
                            path=str(person.get("representative_face_path")),
                            source="person_representative",
                            confidence=None,
                            timestamp=person.get("representative_timestamp"),
                            frame_index=person.get("representative_frame_index"),
                        )
                    )
                if person.get("global_person_id"):
                    _upsert_global_person_from_summary_orm(session, video_id, video_path, person)
            track_payloads = payload.get("tracks") or _tracks_from_segments(payload)
            for track in track_payloads:
                session.add(
                    TrackRow(
                        video_id=video_id,
                        track_id=int(track["track_id"]),
                        person_id=track.get("person_id"),
                        start=float(track.get("start", 0.0)),
                        end=float(track.get("end", 0.0)),
                        detection_count=int(track.get("detection_count", 0)),
                        representative_face_path=track.get("representative_face_path"),
                        representative_bbox_json=json.dumps(
                            track.get("representative_bbox"),
                            ensure_ascii=False,
                        ),
                        representative_confidence=track.get("representative_confidence"),
                        representative_timestamp=track.get("representative_timestamp"),
                        representative_frame_index=track.get("representative_frame_index"),
                        embedding_dim=int(track.get("embedding_dim", 0)),
                        embedding_norm=float(track.get("embedding_norm", 0.0)),
                    )
                )
                if track.get("representative_face_path"):
                    face_crop_rows.append(
                        FaceCropRow(
                            video_id=video_id,
                            person_id=track.get("person_id"),
                            track_id=int(track["track_id"]),
                            path=str(track.get("representative_face_path")),
                            source="track_representative",
                            confidence=track.get("representative_confidence"),
                            timestamp=track.get("representative_timestamp"),
                            frame_index=track.get("representative_frame_index"),
                        )
                    )
                for detection in track.get("detections", []):
                    bbox = detection.get("bbox", detection.get("bbox_xyxy"))
                    if not _valid_bbox(bbox):
                        continue
                    session.add(
                        TrackDetectionRow(
                            video_id=video_id,
                            track_id=int(track["track_id"]),
                            person_id=track.get("person_id"),
                            frame_index=int(detection.get("frame_index", 0)),
                            timestamp=float(detection.get("timestamp", 0.0)),
                            bbox_json=json.dumps(bbox, ensure_ascii=False),
                            confidence=detection.get("confidence"),
                        )
                    )
            for crop in _dedupe_face_crop_rows(face_crop_rows):
                session.add(crop)
            for person_id, segments in payload.get("persons", {}).items():
                for segment in segments:
                    session.add(
                        SegmentRow(
                            video_id=video_id,
                            person_id=int(person_id),
                            start=float(segment["start"]),
                            end=float(segment["end"]),
                            detection_count=int(segment.get("detection_count", 0)),
                            track_ids=json.dumps(segment.get("track_ids", [])),
                            clip_path=segment.get("clip_path"),
                        )
                    )
            _refresh_video_people_count_orm(session, video_id)
        return video_id

    def _init_schema(self) -> None:
        """初始化数据库表结构。"""
        Base.metadata.create_all(self.engine)
        for table in Base.metadata.sorted_tables:
            for index in table.indexes:
                index.create(bind=self.engine, checkfirst=True)
        with session_scope(self.session_factory) as session:
            _backfill_representative_metadata_orm(session)

def _require_person_orm(session: Session, video_id: int, person_id: int) -> PersonRow:
    """断言指定人物存在并返回其记录。"""
    row = session.scalars(
        select(PersonRow).where(PersonRow.video_id == video_id, PersonRow.person_id == person_id)
    ).first()
    if row is None:
        raise ValueError(f"person not found: {person_id}")
    return row


def _require_global_observation_orm(
    session: Session,
    global_person_id: str,
    video_path: str,
    local_person_id: int,
) -> GlobalObservationRow:
    """断言指定全局观测存在并返回其记录。"""
    row = session.scalars(
        select(GlobalObservationRow).where(
            GlobalObservationRow.global_person_id == global_person_id,
            GlobalObservationRow.video_path == video_path,
            GlobalObservationRow.local_person_id == local_person_id,
        )
    ).first()
    if row is None:
        raise ValueError("global observation not found")
    return row


def _record_review_action_orm(
    session: Session,
    video_id: int,
    action: str,
    payload: dict[str, Any],
) -> None:
    """记录一次人工审核操作。"""
    session.add(
        ReviewActionRow(
            video_id=video_id,
            action=action,
            payload_json=json.dumps(payload, ensure_ascii=False),
            created_at=_database_timestamp(),
        )
    )


def _record_global_person_action_orm(
    session: Session,
    global_person_id: str,
    action: str,
    payload: dict[str, Any],
) -> None:
    """记录一次人物档案级操作。"""
    session.add(
        GlobalPersonActionRow(
            global_person_id=global_person_id,
            action=action,
            payload_json=json.dumps(payload, ensure_ascii=False),
            created_at=_database_timestamp(),
        )
    )


def _next_local_person_id_orm(session: Session, video_id: int) -> int:
    """生成视频中下一个可用的本地人物 ID。"""
    next_id = session.scalar(
        select(func.coalesce(func.max(PersonRow.person_id), -1) + 1).where(
            PersonRow.video_id == video_id
        )
    )
    return int(next_id or 0)


def _recompute_person_summary_orm(
    session: Session,
    video_id: int,
    person_id: int,
    fallback: Mapping[str, Any] | None = None,
) -> None:
    """根据片段重新计算人物的汇总统计与代表人脸。"""
    session.flush()
    person = session.scalars(
        select(PersonRow).where(PersonRow.video_id == video_id, PersonRow.person_id == person_id)
    ).first()
    if person is None:
        return
    appearances, total_duration, detection_count = session.execute(
        select(
            func.count(SegmentRow.id),
            func.coalesce(func.sum(SegmentRow.end - SegmentRow.start), 0.0),
            func.coalesce(func.sum(SegmentRow.detection_count), 0),
        ).where(SegmentRow.video_id == video_id, SegmentRow.person_id == person_id)
    ).one()
    face = session.scalars(
        select(FaceCropRow)
        .where(FaceCropRow.video_id == video_id, FaceCropRow.person_id == person_id)
        .order_by(FaceCropRow.confidence.is_(None), FaceCropRow.confidence.desc(), FaceCropRow.id)
        .limit(1)
    ).first()
    person.appearances = int(appearances or 0)
    person.total_duration = float(total_duration or 0.0)
    person.detection_count = int(detection_count or 0)
    person.representative_face_path = (
        face.path
        if face is not None
        else (fallback.get("representative_face_path") if fallback is not None else None)
    )
    person.representative_timestamp = (
        face.timestamp
        if face is not None
        else (fallback.get("representative_timestamp") if fallback is not None else None)
    )
    person.representative_frame_index = (
        face.frame_index
        if face is not None
        else (fallback.get("representative_frame_index") if fallback is not None else None)
    )


def _reassign_segments_from_tracks_orm(
    session: Session,
    video_id: int,
    person_id: int,
) -> None:
    """根据当前轨迹重新生成该人物的片段。"""
    session.flush()
    session.execute(delete(SegmentRow).where(SegmentRow.video_id == video_id, SegmentRow.person_id == person_id))
    tracks = session.scalars(
        select(TrackRow)
        .where(TrackRow.video_id == video_id, TrackRow.person_id == person_id)
        .order_by(TrackRow.start, TrackRow.track_id)
    ).all()
    for track in tracks:
        session.add(
            SegmentRow(
                video_id=video_id,
                person_id=person_id,
                start=track.start,
                end=track.end,
                detection_count=track.detection_count,
                track_ids=json.dumps([track.track_id]),
                clip_path=None,
            )
        )


def _delete_empty_person_orm(session: Session, video_id: int, person_id: int) -> None:
    """删除已经没有轨迹的人物记录。"""
    session.flush()
    count = session.scalar(
        select(func.count(TrackRow.id)).where(
            TrackRow.video_id == video_id,
            TrackRow.person_id == person_id,
        )
    )
    if int(count or 0) == 0:
        person = session.scalars(
            select(PersonRow).where(PersonRow.video_id == video_id, PersonRow.person_id == person_id)
        ).first()
        if person is not None:
            session.delete(person)


def _upsert_global_person_from_summary_orm(
    session: Session,
    video_id: int,
    video_path: str,
    person: dict[str, Any],
) -> None:
    """根据人物摘要更新全局人物与观测记录。"""
    global_person_id = str(person["global_person_id"])
    duration = float(person.get("total_duration", 0.0))
    representative_face_path = person.get("representative_face_path")
    representative_timestamp = person.get("representative_timestamp")
    representative_frame_index = person.get("representative_frame_index")

    global_person = session.get(GlobalPersonRow, global_person_id)
    if global_person is None:
        global_person = GlobalPersonRow(
            global_person_id=global_person_id,
            label=person.get("label"),
            representative_face_path=representative_face_path,
            representative_timestamp=representative_timestamp,
            representative_frame_index=representative_frame_index,
            observation_count=0,
            confirmed_count=0,
            total_duration=duration,
            deleted_at=None,
        )
        session.add(global_person)
    else:
        if not global_person.label:
            global_person.label = person.get("label")
        if global_person.representative_face_path is None:
            global_person.representative_face_path = representative_face_path
        if global_person.representative_timestamp is None:
            global_person.representative_timestamp = representative_timestamp
        if global_person.representative_frame_index is None:
            global_person.representative_frame_index = representative_frame_index
        global_person.total_duration = float(global_person.total_duration or 0.0) + duration

    observation = session.scalars(
        select(GlobalObservationRow).where(
            GlobalObservationRow.global_person_id == global_person_id,
            GlobalObservationRow.video_path == video_path,
            GlobalObservationRow.local_person_id == int(person["person_id"]),
        )
    ).first()
    if observation is None:
        observation = GlobalObservationRow(
            global_person_id=global_person_id,
            video_id=video_id,
            video_path=video_path,
            local_person_id=int(person["person_id"]),
            label=str(person.get("label") or ""),
            representative_face_path=representative_face_path,
            representative_timestamp=representative_timestamp,
            representative_frame_index=representative_frame_index,
            appearances=int(person.get("appearances", 0)),
            total_duration=duration,
            detection_count=int(person.get("detection_count", 0)),
            confirmed=0,
            rejected=0,
            hidden=int(person.get("hidden", 0) or 0),
        )
        session.add(observation)
    else:
        observation.video_id = video_id
        observation.label = str(person.get("label") or "")
        observation.representative_face_path = representative_face_path
        observation.representative_timestamp = representative_timestamp
        observation.representative_frame_index = representative_frame_index
        observation.appearances = int(person.get("appearances", 0))
        observation.total_duration = duration
        observation.detection_count = int(person.get("detection_count", 0))
        observation.hidden = int(person.get("hidden", 0) or 0)

    session.flush()
    _refresh_global_person_summary_orm(session, global_person_id)


def _refresh_video_people_count_orm(session: Session, video_id: int) -> None:
    """刷新视频的当前人物数量。"""
    session.flush()
    count = session.scalar(
        select(func.count(PersonRow.id)).where(
            PersonRow.video_id == video_id,
            PersonRow.hidden == 0,
        )
    )
    video = session.get(VideoRow, video_id)
    if video is not None:
        video.people_count = int(count or 0)


def _refresh_global_person_summary_orm(session: Session, global_person_id: str) -> None:
    """根据观测记录刷新全局人物的汇总统计。"""
    session.flush()
    existing = session.get(GlobalPersonRow, global_person_id)
    observation_count, confirmed_count, total_duration, label = session.execute(
        select(
            func.count(GlobalObservationRow.id),
            func.coalesce(func.sum(GlobalObservationRow.confirmed), 0),
            func.coalesce(func.sum(GlobalObservationRow.total_duration), 0.0),
            func.max(GlobalObservationRow.label),
        ).where(
            GlobalObservationRow.global_person_id == global_person_id,
            GlobalObservationRow.hidden == 0,
        )
    ).one()
    face = session.scalars(
        select(GlobalObservationRow)
        .where(
            GlobalObservationRow.global_person_id == global_person_id,
            GlobalObservationRow.hidden == 0,
            GlobalObservationRow.representative_face_path.is_not(None),
        )
        .order_by(GlobalObservationRow.confirmed.desc(), GlobalObservationRow.id)
        .limit(1)
    ).first()
    next_label = existing.label if existing is not None and existing.label else label
    if existing is None:
        existing = GlobalPersonRow(
            global_person_id=global_person_id,
            label=next_label,
            representative_face_path=None,
            representative_timestamp=None,
            representative_frame_index=None,
            observation_count=0,
            confirmed_count=0,
            total_duration=0.0,
            deleted_at=None,
        )
        session.add(existing)

    existing.label = next_label
    existing.representative_face_path = (
        face.representative_face_path
        if face is not None
        else existing.representative_face_path
    )
    existing.representative_timestamp = (
        face.representative_timestamp
        if face is not None
        else existing.representative_timestamp
    )
    existing.representative_frame_index = (
        face.representative_frame_index
        if face is not None
        else existing.representative_frame_index
    )
    existing.observation_count = int(observation_count or 0)
    existing.confirmed_count = int(confirmed_count or 0)
    existing.total_duration = float(total_duration or 0.0)


def _manual_global_person_id() -> str:
    """生成手动建档 ID，避免和自动识别的 global_person_000001 序列碰撞。"""
    return f"manual_person_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"


def _backfill_representative_metadata_orm(session: Session) -> None:
    """用已有逐帧检测回填旧库缺失的代表截图来源帧。"""
    tracks = session.scalars(
        select(TrackRow).where(
            TrackRow.representative_face_path.is_not(None),
            or_(
                TrackRow.representative_timestamp.is_(None),
                TrackRow.representative_frame_index.is_(None),
            ),
        )
    ).all()
    for track in tracks:
        detection = session.scalars(
            select(TrackDetectionRow)
            .where(
                TrackDetectionRow.video_id == track.video_id,
                TrackDetectionRow.track_id == track.track_id,
            )
            .order_by(
                TrackDetectionRow.confidence.is_(None),
                TrackDetectionRow.confidence.desc(),
                TrackDetectionRow.id,
            )
            .limit(1)
        ).first()
        if detection is None:
            continue
        if track.representative_timestamp is None:
            track.representative_timestamp = detection.timestamp
        if track.representative_frame_index is None:
            track.representative_frame_index = detection.frame_index

    face_crops = session.scalars(
        select(FaceCropRow).where(
            FaceCropRow.track_id.is_not(None),
            or_(FaceCropRow.timestamp.is_(None), FaceCropRow.frame_index.is_(None)),
        )
    ).all()
    for crop in face_crops:
        track = session.scalars(
            select(TrackRow).where(
                TrackRow.video_id == crop.video_id,
                TrackRow.track_id == crop.track_id,
            )
        ).first()
        if track is None:
            continue
        if crop.timestamp is None:
            crop.timestamp = track.representative_timestamp
        if crop.frame_index is None:
            crop.frame_index = track.representative_frame_index

    people = session.scalars(
        select(PersonRow).where(
            PersonRow.representative_face_path.is_not(None),
            or_(
                PersonRow.representative_timestamp.is_(None),
                PersonRow.representative_frame_index.is_(None),
            ),
        )
    ).all()
    for person in people:
        face = session.scalars(
            select(FaceCropRow)
            .where(
                FaceCropRow.video_id == person.video_id,
                FaceCropRow.person_id == person.person_id,
                FaceCropRow.timestamp.is_not(None),
            )
            .order_by(
                FaceCropRow.confidence.is_(None),
                FaceCropRow.confidence.desc(),
                FaceCropRow.id,
            )
            .limit(1)
        ).first()
        if face is None:
            continue
        if person.representative_timestamp is None:
            person.representative_timestamp = face.timestamp
        if person.representative_frame_index is None:
            person.representative_frame_index = face.frame_index
        representative_crops = session.scalars(
            select(FaceCropRow).where(
                FaceCropRow.video_id == person.video_id,
                FaceCropRow.person_id == person.person_id,
                FaceCropRow.source == "person_representative",
            )
        ).all()
        for crop in representative_crops:
            if crop.timestamp is None:
                crop.timestamp = face.timestamp
            if crop.frame_index is None:
                crop.frame_index = face.frame_index

    observations = session.scalars(
        select(GlobalObservationRow).where(
            GlobalObservationRow.representative_face_path.is_not(None),
            or_(
                GlobalObservationRow.representative_timestamp.is_(None),
                GlobalObservationRow.representative_frame_index.is_(None),
            ),
        )
    ).all()
    for observation in observations:
        person = session.scalars(
            select(PersonRow).where(
                PersonRow.video_id == observation.video_id,
                PersonRow.person_id == observation.local_person_id,
            )
        ).first()
        if person is None:
            continue
        if observation.representative_timestamp is None:
            observation.representative_timestamp = person.representative_timestamp
        if observation.representative_frame_index is None:
            observation.representative_frame_index = person.representative_frame_index

    session.flush()
    global_person_ids = session.scalars(
        select(GlobalObservationRow.global_person_id)
        .where(GlobalObservationRow.representative_timestamp.is_not(None))
        .distinct()
    ).all()
    for global_person_id in global_person_ids:
        _refresh_global_person_summary_orm(session, global_person_id)


def _model_payload(row: Any) -> dict[str, Any]:
    """把 ORM 行对象转换为 API/前端可直接使用的字典。"""
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def _dedupe_face_crop_rows(rows: list[FaceCropRow]) -> list[FaceCropRow]:
    """合并同一人物同一帧的候选截图，避免 person/track 代表图重复展示。"""
    selected: dict[tuple[Any, ...], FaceCropRow] = {}
    order: dict[tuple[Any, ...], int] = {}
    for index, row in enumerate(rows):
        key = _face_crop_dedupe_key(row)
        if key not in selected:
            selected[key] = row
            order[key] = index
            continue
        if _face_crop_rank(row) > _face_crop_rank(selected[key]):
            selected[key] = row
    return [selected[key] for key in sorted(order, key=order.__getitem__)]


def _face_crop_payloads_with_bboxes(session: Session, rows: list[FaceCropRow]) -> list[dict[str, Any]]:
    """给截图候选补上同一帧的人脸框，供前端在完整画面上标记位置。"""
    payloads = [_model_payload(row) for row in rows]
    if not rows:
        return payloads

    video_ids = {int(row.video_id) for row in rows}
    frame_indexes = {int(row.frame_index) for row in rows if row.frame_index is not None}
    timestamp_rows = [row for row in rows if row.timestamp is not None]
    filters = []
    if frame_indexes:
        filters.append(TrackDetectionRow.frame_index.in_(frame_indexes))
    if timestamp_rows:
        min_timestamp = min(float(row.timestamp) for row in timestamp_rows) - 0.05
        max_timestamp = max(float(row.timestamp) for row in timestamp_rows) + 0.05
        filters.append(
            TrackDetectionRow.timestamp.between(
                max(min_timestamp, 0.0),
                max_timestamp,
            )
        )
    if not filters:
        for payload in payloads:
            payload["bbox_json"] = None
        return payloads

    detections = session.scalars(
        select(TrackDetectionRow)
        .where(TrackDetectionRow.video_id.in_(video_ids))
        .where(or_(*filters))
        .order_by(TrackDetectionRow.timestamp, TrackDetectionRow.track_id)
    ).all()
    for payload, row in zip(payloads, rows, strict=True):
        detection = _best_detection_for_face_crop(row, detections)
        payload["bbox_json"] = detection.bbox_json if detection is not None else None
    return payloads


def _best_detection_for_face_crop(
    row: FaceCropRow,
    detections: list[TrackDetectionRow],
) -> TrackDetectionRow | None:
    """按同 track、同 person、同帧/近时间点优先选择截图对应的人脸框。"""
    best_detection: TrackDetectionRow | None = None
    best_score: tuple[int, int, float, float, int] | None = None
    for detection in detections:
        if int(detection.video_id) != int(row.video_id):
            continue
        track_match = row.track_id is not None and int(detection.track_id) == int(row.track_id)
        person_match = row.person_id is not None and detection.person_id == row.person_id
        if not track_match and not person_match:
            continue

        frame_match = row.frame_index is not None and int(detection.frame_index) == int(row.frame_index)
        timestamp_delta = (
            abs(float(detection.timestamp) - float(row.timestamp))
            if row.timestamp is not None
            else float("inf")
        )
        if not frame_match and timestamp_delta > 0.05:
            continue

        score = (
            int(track_match),
            int(frame_match),
            -timestamp_delta if timestamp_delta != float("inf") else 0.0,
            float(detection.confidence) if detection.confidence is not None else -1.0,
            -int(detection.id or 0),
        )
        if best_score is None or score > best_score:
            best_score = score
            best_detection = detection
    return best_detection


def _face_crop_dedupe_key(row: FaceCropRow) -> tuple[Any, ...]:
    """生成候选截图去重键；有帧号时按帧号，没有帧号时按时间点兜底。"""
    return _face_crop_values_key(
        row.video_id,
        row.person_id,
        row.path,
        row.timestamp,
        row.frame_index,
    )


def _face_crop_values_key(
    video_id: int,
    person_id: int | None,
    path: str,
    timestamp: float | None,
    frame_index: int | None,
) -> tuple[Any, ...]:
    """把截图定位信息归一化为稳定键。"""
    normalized_person_id = int(person_id) if person_id is not None else None
    if normalized_person_id is not None and frame_index is not None:
        return ("person_frame", int(video_id), normalized_person_id, int(frame_index))
    if normalized_person_id is not None and timestamp is not None:
        return ("person_time", int(video_id), normalized_person_id, round(float(timestamp), 3))
    return ("path", int(video_id), normalized_person_id, str(path))


def _face_crop_rank(row: FaceCropRow) -> tuple[int, int, int, float, int]:
    """同一帧出现多条截图时，优先保留带 track/置信度的信息。"""
    confidence = float(row.confidence) if row.confidence is not None else -1.0
    source_priority = 2 if row.source == "track_representative" else 1
    row_id = int(row.id or 0)
    return (
        source_priority,
        int(row.track_id is not None),
        int(row.confidence is not None),
        confidence,
        -row_id,
    )


def _video_model_payload(row: VideoRow) -> dict[str, Any]:
    """把 ORM 视频行转换为 API/前端可直接使用的字典。"""
    return _video_payload(_model_payload(row))


def _video_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """补齐视频行的派生字段。"""
    diagnostics = _parse_json_object(payload.get("diagnostics_json"))
    elapsed = diagnostics.get("elapsed_seconds")
    payload["analysis_elapsed_seconds"] = (
        float(elapsed) if isinstance(elapsed, int | float) else None
    )
    return payload


def _analyze_job_payload(row: AnalyzeJobRow) -> dict[str, Any]:
    """把分析任务行中的 JSON 快照还原为 API 结构。"""
    payload = json.loads(row.payload_json)
    payload["created_at"] = row.created_at
    payload["updated_at"] = row.updated_at
    return payload


def _database_timestamp() -> str:
    """生成数据库中使用的 UTC 时间戳字符串。"""
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _parse_json_object(raw: Any) -> dict[str, Any]:
    """安全解析 SQLite 中保存的 JSON 对象。"""
    if not isinstance(raw, str) or not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


_GENERATED_TITLE_RE = re.compile(r"^(?:[0-9a-fA-F]{16,}|[0-9a-fA-F-]{24,})$")


def _first_non_empty(*values: Any) -> str:
    """返回第一个非空字符串。"""
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _is_generated_title(value: str) -> bool:
    """判断标题是否像 UUID/MD5 这类内部生成 ID。"""
    stem = Path(value).stem.strip()
    return bool(_GENERATED_TITLE_RE.fullmatch(stem))


def _video_display_title(
    *,
    video_path: str,
    display_title: str | None,
    original_filename: str | None,
    existing_title: str | None,
    payload_title: str | None,
) -> str:
    """生成视频列表中展示用的作品标题。"""
    candidates = (
        (display_title, True),
        (existing_title, False),
        (original_filename, True),
        (payload_title, False),
    )
    for candidate, allow_generated in candidates:
        if candidate and candidate.strip() and (allow_generated or not _is_generated_title(candidate)):
            return Path(candidate.strip()).stem
    return Path(video_path).stem


def _valid_bbox(value: Any) -> bool:
    """判断 bbox 是否为 [x1, y1, x2, y2] 数字列表。"""
    if not isinstance(value, list) or len(value) != 4:
        return False
    return all(isinstance(item, int | float) for item in value)


def _tracks_from_segments(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """从旧版 timeline 的 segment.track_ids 补出基础轨迹记录。"""
    tracks: dict[int, dict[str, Any]] = {}
    for person_id, segments in payload.get("persons", {}).items():
        for segment in segments:
            track_ids = segment.get("track_ids") or []
            detection_count = int(segment.get("detection_count", 0))
            per_track_count = max(detection_count // max(len(track_ids), 1), 0)
            for track_id in track_ids:
                current = tracks.get(int(track_id))
                if current is None:
                    tracks[int(track_id)] = {
                        "track_id": int(track_id),
                        "person_id": int(person_id),
                        "start": float(segment.get("start", 0.0)),
                        "end": float(segment.get("end", 0.0)),
                        "detection_count": per_track_count,
                        "representative_face_path": None,
                        "representative_bbox": None,
                        "representative_confidence": None,
                        "embedding_dim": 0,
                        "embedding_norm": 0.0,
                    }
                    continue
                current["start"] = min(current["start"], float(segment.get("start", 0.0)))
                current["end"] = max(current["end"], float(segment.get("end", 0.0)))
                current["detection_count"] += per_track_count
    return [tracks[track_id] for track_id in sorted(tracks)]

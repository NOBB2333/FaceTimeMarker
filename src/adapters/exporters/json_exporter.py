from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from core.models import AnalysisResult, VideoInfo


class JsonTimelineExporter:
    """人物时间轴 JSON 导出器。"""

    def __init__(self, output_dir: Path) -> None:
        """初始化 JSON 输出目录。"""
        self.output_dir = output_dir

    def write(self, result: AnalysisResult) -> Path:
        """将分析结果写入 timeline.json 并返回文件路径。"""
        path = self.output_dir / "timeline.json"
        payload = {
            "video": _video_to_json(result.video),
            "diagnostics": _diagnostics_to_json(result.diagnostics),
            "people_count": len(result.people),
            "people": [_person_to_json(person) for person in result.people],
            "tracks": [_track_to_json(track) for track in result.tracks],
            "persons": {
                str(person_id): [_segment_to_json(segment) for segment in segments]
                for person_id, segments in result.persons.items()
            },
        }
        self._write_json(path, payload)
        return path

    def write_dry_run(self, video: VideoInfo, config: BaseModel) -> Path:
        """写入 dry_run 验证结果，不执行视觉推理。"""
        path = self.output_dir / "dry_run.json"
        payload: dict[str, Any] = {
            "status": "dry_run",
            "video": _video_to_json(video),
            "config": config.model_dump(mode="json", by_alias=True),
            "message": "已验证配置和视频读取；未运行视觉推理。",
        }
        self._write_json(path, payload)
        return path

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        """将字典序列化为 JSON 文件。"""
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _video_to_json(video: VideoInfo) -> dict[str, Any]:
    """将 VideoInfo 转为可序列化的字典。"""
    payload = asdict(video)
    payload["path"] = str(video.path)
    return payload


def _person_to_json(person) -> dict[str, Any]:
    """将 PersonSummary 转为 JSON 字典。"""
    return {
        "person_id": person.person_id,
        "label": person.label,
        "global_person_id": person.global_person_id,
        "track_ids": list(person.track_ids),
        "appearances": person.appearances,
        "total_duration": round(person.total_duration, 3),
        "detection_count": person.detection_count,
        "representative_face_path": (
            str(person.representative_face_path)
            if person.representative_face_path is not None
            else None
        ),
        "representative_timestamp": (
            round(person.representative_timestamp, 3)
            if person.representative_timestamp is not None
            else None
        ),
        "representative_frame_index": person.representative_frame_index,
    }


def _diagnostics_to_json(diagnostics) -> dict[str, Any] | None:
    """将 AnalysisDiagnostics 转为 JSON 字典。"""
    if diagnostics is None:
        return None
    return {
        "sampled_frames": diagnostics.sampled_frames,
        "raw_faces": diagnostics.raw_faces,
        "kept_faces": diagnostics.kept_faces,
        "filtered_small_faces": diagnostics.filtered_small_faces,
        "tracks": diagnostics.tracks,
        "people": diagnostics.people,
        "elapsed_seconds": round(diagnostics.elapsed_seconds, 3),
        "frames_per_second": round(diagnostics.frames_per_second, 3),
        "average_face_width": round(diagnostics.average_face_width, 3),
        "average_face_height": round(diagnostics.average_face_height, 3),
        "preset": diagnostics.preset,
        "cache_hit": diagnostics.cache_hit,
    }


def _segment_to_json(segment) -> dict[str, Any]:
    """将 TimelineSegment 转为 JSON 字典。"""
    return {
        "person_id": segment.person_id,
        "start": round(segment.start, 3),
        "end": round(segment.end, 3),
        "track_ids": list(segment.track_ids),
        "detection_count": segment.detection_count,
        "clip_path": str(segment.clip_path) if segment.clip_path is not None else None,
    }


def _track_to_json(track) -> dict[str, Any]:
    """将 FaceTrack 转为 JSON 字典，供 SQLite 和审阅界面复用。"""
    representative = track.representative_detection
    return {
        "track_id": track.track_id,
        "person_id": track.person_id,
        "start": round(track.start, 3) if track.detections else 0.0,
        "end": round(track.end, 3) if track.detections else 0.0,
        "detection_count": len(track.detections),
        "representative_face_path": (
            str(track.representative_face_path)
            if track.representative_face_path is not None
            else None
        ),
        "representative_bbox": (
            list(representative.bbox_xyxy) if representative is not None else None
        ),
        "representative_confidence": (
            round(representative.confidence, 6) if representative is not None else None
        ),
        "representative_timestamp": (
            round(representative.timestamp, 3) if representative is not None else None
        ),
        "representative_frame_index": representative.frame_index if representative is not None else None,
        "detections": [_detection_to_json(detection) for detection in track.detections],
        "embedding_dim": int(track.embedding.shape[0]) if track.embedding is not None else 0,
        "embedding_norm": (
            round(float((track.embedding**2).sum() ** 0.5), 6)
            if track.embedding is not None
            else 0.0
        ),
    }


def _detection_to_json(detection) -> dict[str, Any]:
    """将单次人脸检测转为 JSON 字典，用于逐帧红框。"""
    return {
        "frame_index": detection.frame_index,
        "timestamp": round(detection.timestamp, 3),
        "bbox": list(detection.bbox_xyxy),
        "confidence": round(detection.confidence, 6),
    }

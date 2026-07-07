from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from core.models import FaceDetection, FaceTrack

STAGE_CACHE_VERSION = 1


@dataclass(frozen=True)
class DetectionFrameCache:
    """单个抽样帧的检测缓存。"""

    frame_index: int  # 帧序号
    timestamp: float  # 时间戳（秒）
    detections: list[FaceDetection]  # 该帧检测到的人脸列表


@dataclass(frozen=True)
class StageCacheStats:
    """阶段缓存携带的诊断统计。"""

    sampled_frames: int = 0  # 采样帧数
    raw_faces: int = 0  # 原始检测到的人脸数
    kept_faces: int = 0  # 过滤后保留的人脸数
    face_width_sum: float = 0.0  # 人脸宽度总和
    face_height_sum: float = 0.0  # 人脸高度总和
    face_size_count: int = 0  # 统计人脸尺寸的数量

    @property
    def average_face_width(self) -> float:
        """返回平均人脸宽度。"""
        if self.face_size_count <= 0:
            return 0.0
        return self.face_width_sum / self.face_size_count

    @property
    def average_face_height(self) -> float:
        """返回平均人脸高度。"""
        if self.face_size_count <= 0:
            return 0.0
        return self.face_height_sum / self.face_size_count


def read_detection_cache(path: Path) -> tuple[list[DetectionFrameCache], StageCacheStats] | None:
    """读取逐帧检测和 embedding 缓存。"""
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("version") != STAGE_CACHE_VERSION:
        return None
    frames = [
        DetectionFrameCache(
            frame_index=int(frame["frame_index"]),
            timestamp=float(frame["timestamp"]),
            detections=[_detection_from_json(item) for item in frame.get("detections", [])],
        )
        for frame in payload.get("frames", [])
    ]
    return frames, _stats_from_json(payload.get("stats") or {})


def write_detection_cache(
    path: Path,
    frames: list[DetectionFrameCache],
    stats: StageCacheStats,
) -> None:
    """写入逐帧检测和 embedding 缓存。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": STAGE_CACHE_VERSION,
        "kind": "detections",
        "stats": _stats_to_json(stats),
        "frames": [
            {
                "frame_index": frame.frame_index,
                "timestamp": frame.timestamp,
                "detections": [_detection_to_json(detection) for detection in frame.detections],
            }
            for frame in frames
        ],
    }
    _write_json(path, payload)


def read_track_cache(path: Path) -> tuple[list[FaceTrack], StageCacheStats] | None:
    """读取 track 和轨迹 embedding 缓存。"""
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("version") != STAGE_CACHE_VERSION:
        return None
    tracks = [_track_from_json(item) for item in payload.get("tracks", [])]
    return tracks, _stats_from_json(payload.get("stats") or {})


def write_track_cache(path: Path, tracks: list[FaceTrack], stats: StageCacheStats) -> None:
    """写入 track 和轨迹 embedding 缓存。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": STAGE_CACHE_VERSION,
        "kind": "tracks",
        "stats": _stats_to_json(stats),
        "tracks": [_track_to_json(track) for track in tracks],
    }
    _write_json(path, payload)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    """将字典写入 JSON 文件。"""
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _stats_to_json(stats: StageCacheStats) -> dict[str, Any]:
    """将 StageCacheStats 序列化为字典。"""
    return {
        "sampled_frames": stats.sampled_frames,
        "raw_faces": stats.raw_faces,
        "kept_faces": stats.kept_faces,
        "face_width_sum": stats.face_width_sum,
        "face_height_sum": stats.face_height_sum,
        "face_size_count": stats.face_size_count,
    }


def _stats_from_json(payload: dict[str, Any]) -> StageCacheStats:
    """从字典反序列化 StageCacheStats。"""
    return StageCacheStats(
        sampled_frames=int(payload.get("sampled_frames", 0)),
        raw_faces=int(payload.get("raw_faces", 0)),
        kept_faces=int(payload.get("kept_faces", 0)),
        face_width_sum=float(payload.get("face_width_sum", 0.0)),
        face_height_sum=float(payload.get("face_height_sum", 0.0)),
        face_size_count=int(payload.get("face_size_count", 0)),
    )


def _track_to_json(track: FaceTrack) -> dict[str, Any]:
    """将 FaceTrack 序列化为字典。"""
    return {
        "track_id": track.track_id,
        "detections": [_detection_to_json(detection) for detection in track.detections],
        "embedding": _array_to_json(track.embedding),
        "representative_detection": (
            _detection_to_json(track.representative_detection)
            if track.representative_detection is not None
            else None
        ),
        "representative_face_path": (
            str(track.representative_face_path)
            if track.representative_face_path is not None
            else None
        ),
    }


def _track_from_json(payload: dict[str, Any]) -> FaceTrack:
    """从字典反序列化 FaceTrack。"""
    return FaceTrack(
        track_id=int(payload["track_id"]),
        detections=[_detection_from_json(item) for item in payload.get("detections", [])],
        embedding=_array_from_json(payload.get("embedding")),
        representative_detection=(
            _detection_from_json(payload["representative_detection"])
            if payload.get("representative_detection") is not None
            else None
        ),
        representative_face_path=(
            Path(payload["representative_face_path"])
            if payload.get("representative_face_path") is not None
            else None
        ),
    )


def _detection_to_json(detection: FaceDetection) -> dict[str, Any]:
    """将 FaceDetection 序列化为字典。"""
    return {
        "frame_index": detection.frame_index,
        "timestamp": detection.timestamp,
        "bbox_xyxy": list(detection.bbox_xyxy),
        "confidence": detection.confidence,
        "embedding": _array_to_json(detection.embedding),
        "landmarks": _array_to_json(detection.landmarks),
    }


def _detection_from_json(payload: dict[str, Any]) -> FaceDetection:
    """从字典反序列化 FaceDetection。"""
    return FaceDetection(
        frame_index=int(payload["frame_index"]),
        timestamp=float(payload["timestamp"]),
        bbox_xyxy=tuple(float(value) for value in payload["bbox_xyxy"]),
        confidence=float(payload["confidence"]),
        embedding=_array_from_json(payload.get("embedding")),
        landmarks=_array_from_json(payload.get("landmarks")),
    )


def _array_to_json(array: np.ndarray | None) -> list[Any] | None:
    """将 numpy 数组序列化为列表。"""
    if array is None:
        return None
    return array.tolist()


def _array_from_json(payload: list[Any] | None) -> np.ndarray | None:
    """从列表反序列化为 float32 numpy 数组。"""
    if payload is None:
        return None
    return np.array(payload, dtype=np.float32)

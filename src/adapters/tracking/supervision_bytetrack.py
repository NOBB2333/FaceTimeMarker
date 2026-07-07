from __future__ import annotations

import numpy as np

from core.config import TrackingConfig
from core.models import FaceDetection, TrackedFace


class SupervisionByteTracker:
    """基于 supervision 的 ByteTrack 跟踪器适配器。"""

    def __init__(self, config: TrackingConfig, frame_rate: int) -> None:
        """初始化 ByteTrack 配置与视频帧率。"""
        self.config = config
        self.frame_rate = frame_rate
        self._tracker = None

    def load(self) -> None:
        """加载 supervision ByteTrack 跟踪器。"""
        try:
            import supervision as sv
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("未安装 supervision，请运行：uv sync --extra vision") from exc

        self._sv = sv
        self._tracker = sv.ByteTrack(
            track_activation_threshold=self.config.track_activation_threshold,
            lost_track_buffer=self.config.lost_track_buffer,
            minimum_matching_threshold=self.config.minimum_matching_threshold,
            minimum_consecutive_frames=self.config.minimum_consecutive_frames,
            frame_rate=self.frame_rate,
        )

    def update(
        self,
        detections: list[FaceDetection],
        image: np.ndarray | None = None,
    ) -> list[TrackedFace]:
        """用 ByteTrack 更新一帧跟踪结果。"""
        if self._tracker is None:
            self.load()

        if not detections:
            return []

        # 构造 supervision.Detections 所需字段
        boxes = np.array([d.bbox_xyxy for d in detections], dtype=np.float32)
        confidence = np.array([d.confidence for d in detections], dtype=np.float32)
        class_id = np.zeros(len(detections), dtype=int)

        sv_detections = self._sv.Detections(
            xyxy=boxes,
            confidence=confidence,
            class_id=class_id,
        )
        tracked = self._tracker.update_with_detections(sv_detections)
        if tracked.tracker_id is None:
            return []

        results: list[TrackedFace] = []
        for index, track_id in enumerate(tracked.tracker_id):
            results.append(TrackedFace(track_id=int(track_id), detection=detections[index]))
        return results

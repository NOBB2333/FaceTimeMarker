from __future__ import annotations

import numpy as np

from core.config import TrackingConfig
from core.models import FaceDetection, TrackedFace


class BoxmotBotSortTracker:
    """面向 InsightFace 检测结果的 BoT-SORT 适配器。

    这是当前默认跟踪器。它被包在本项目的 FaceTracker 协议后面，
    后续要替换成 DeepOCSORT 或其他跟踪器时，不需要改动后续聚类和导出层。
    """

    def __init__(self, config: TrackingConfig, device: str = "cpu") -> None:
        """初始化跟踪器配置与推理设备。"""
        self.config = config
        self.device = device
        self._tracker = None

    def load(self) -> None:
        """加载 BoxMOT BoT-SORT 跟踪器。"""
        try:
            from boxmot.trackers.bbox.botsort.botsort import BotSort
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("未安装 BoxMOT，请运行：uv sync --extra vision") from exc

        self._tracker = BotSort(
            reid_model=None,
            track_high_thresh=self.config.track_activation_threshold,
            track_buffer=self.config.lost_track_buffer,
            match_thresh=self.config.minimum_matching_threshold,
            proximity_thresh=self.config.proximity_threshold,
            appearance_thresh=self.config.appearance_threshold,
            cmc_method=self.config.cmc_method,
            min_hits=self.config.minimum_consecutive_frames,
            with_reid=True,
        )

    def update(self, detections: list[FaceDetection], image: np.ndarray) -> list[TrackedFace]:
        """用 BoT-SORT 更新一帧跟踪结果，返回检测与轨迹 ID 的映射。"""
        if self._tracker is None:
            self.load()

        # 构造 [x1, y1, x2, y2, conf, class] 格式的检测输入
        dets = np.array(
            [[*detection.bbox_xyxy, detection.confidence, 0] for detection in detections],
            dtype=np.float32,
        )
        embeddings = _embeddings_or_none(detections)
        tracks = self._tracker.update(dets, image, embs=embeddings)

        # 按 tracker 返回的 det_ind 映射回原始检测
        results: list[TrackedFace] = []
        for track_id, det_index in zip(tracks.id, tracks.det_ind, strict=True):
            if det_index < 0 or det_index >= len(detections):
                continue
            results.append(
                TrackedFace(
                    track_id=int(track_id),
                    detection=detections[int(det_index)],
                )
            )
        return results


def _embeddings_or_none(detections: list[FaceDetection]) -> np.ndarray | None:
    """提取所有检测的 embedding，任一缺失则返回 None。"""
    if not detections:
        return np.empty((0, 0), dtype=np.float32)
    embeddings = [detection.embedding for detection in detections]
    if any(embedding is None for embedding in embeddings):
        return None
    return np.vstack(embeddings).astype(np.float32)

from __future__ import annotations

from typing import Protocol

import numpy as np

from core.models import FaceDetection, TrackedFace


class FaceTracker(Protocol):
    """人脸跟踪器协议：为当前帧检测分配稳定的轨迹 ID。"""

    def update(self, detections: list[FaceDetection], image: np.ndarray) -> list[TrackedFace]:
        """给当前帧检测结果分配连续帧内稳定的 Track ID。"""

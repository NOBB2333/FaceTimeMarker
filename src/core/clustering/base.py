from __future__ import annotations

from typing import Protocol

from core.models import FaceTrack


class FaceClusterer(Protocol):
    """人脸聚类器协议：为轨迹分配人物 ID。"""

    def assign_person_ids(self, tracks: list[FaceTrack]) -> list[FaceTrack]:
        """根据 embedding 对轨迹分组并分配人物 ID。"""

from __future__ import annotations

from typing import Protocol

from core.models import FaceDetection, Frame


class FaceAnalyzer(Protocol):
    """人脸分析器协议：检测单帧中的人脸。"""

    def analyze(self, frame: Frame) -> list[FaceDetection]:
        """返回单帧内的人脸检测结果和人脸向量。"""

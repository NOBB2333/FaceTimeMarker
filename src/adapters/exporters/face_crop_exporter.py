from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from core.models import FaceDetection, Frame


class FaceCropExporter:
    """人脸截图导出器。"""

    def __init__(self, output_dir: Path) -> None:
        """初始化人脸截图输出目录。"""
        self.output_dir = output_dir / "faces"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write(
        self,
        frame: Frame,
        detection: FaceDetection,
        person_id: int,
        padding_ratio: float = 0.25,
    ) -> Path:
        """从帧中裁剪出指定人物的人脸并保存为图片。"""
        crop = _crop_face(frame, detection, padding_ratio)
        path = self.output_dir / f"person_{person_id + 1:03d}.jpg"
        ok = cv2.imwrite(str(path), crop)
        if not ok:
            raise RuntimeError(f"Failed to write face crop: {path}")
        return path


def _crop_face(frame: Frame, detection: FaceDetection, padding_ratio: float) -> np.ndarray:
    """按边界框和 padding 比例裁剪人脸区域，并做边界保护。"""
    image = frame.image
    height, width = image.shape[:2]
    x1, y1, x2, y2 = detection.bbox_xyxy
    box_width = max(x2 - x1, 1.0)
    box_height = max(y2 - y1, 1.0)
    pad_x = box_width * padding_ratio
    pad_y = box_height * padding_ratio

    # 按 padding 扩展边界框后限制在图像范围内
    left = max(int(round(x1 - pad_x)), 0)
    top = max(int(round(y1 - pad_y)), 0)
    right = min(int(round(x2 + pad_x)), width)
    bottom = min(int(round(y2 + pad_y)), height)

    if right <= left or bottom <= top:
        return image
    return image[top:bottom, left:right]

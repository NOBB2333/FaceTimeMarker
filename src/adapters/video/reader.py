from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import cv2

from core.models import Frame, VideoInfo


def probe_video(path: Path) -> VideoInfo:
    """探测视频基本信息（帧率、帧数、分辨率）。"""
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError(f"Cannot open video: {path}")

    try:
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    finally:
        capture.release()

    return VideoInfo(path=path, fps=fps, frame_count=frame_count, width=width, height=height)


def iter_sampled_frames(path: Path, sample_fps: float) -> Iterator[Frame]:
    """按目标采样帧率迭代读取视频帧。"""
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError(f"Cannot open video: {path}")

    source_fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    if source_fps <= 0:
        capture.release()
        raise ValueError(f"Cannot determine FPS for video: {path}")

    step = max(int(round(source_fps / sample_fps)), 1)
    frame_index = 0

    try:
        while True:
            ok, image = capture.read()
            if not ok:
                break
            # 每隔 step 帧取一帧，实现按 sample_fps 采样
            if frame_index % step == 0:
                yield Frame(
                    index=frame_index,
                    timestamp=frame_index / source_fps,
                    image=image,
                )
            frame_index += 1
    finally:
        capture.release()

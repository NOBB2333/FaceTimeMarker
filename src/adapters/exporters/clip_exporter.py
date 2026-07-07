from __future__ import annotations

from pathlib import Path

import cv2

from core.models import TimelineSegment, VideoInfo


class PersonClipExporter:
    """人物片段视频导出器。"""

    def __init__(self, output_dir: Path) -> None:
        """初始化导出目录。"""
        self.output_dir = output_dir / "clips"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write(self, video: VideoInfo, segment: TimelineSegment, index: int) -> Path:
        """为指定人物片段生成短视频文件并返回路径。"""
        path = self.output_dir / f"person_{segment.person_id + 1:03d}_{index:03d}.mp4"
        _write_clip(video, segment, path)
        return path


def _write_clip(video: VideoInfo, segment: TimelineSegment, path: Path) -> None:
    """用 OpenCV 截取视频指定时间范围的帧并写入新视频文件。"""
    capture = cv2.VideoCapture(str(video.path))
    if not capture.isOpened():
        raise ValueError(f"Cannot open video: {video.path}")

    fps = video.fps if video.fps > 0 else float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    if fps <= 0:
        capture.release()
        raise ValueError(f"Cannot determine FPS for video: {video.path}")

    width = video.width or int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = video.height or int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    # 把时间范围转换为起始帧和结束帧
    start_frame = max(int(segment.start * fps), 0)
    end_frame = max(int(segment.end * fps), start_frame + 1)

    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )
    if not writer.isOpened():
        capture.release()
        raise RuntimeError(f"Cannot write clip: {path}")

    try:
        capture.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        for _ in range(start_frame, end_frame):
            ok, frame = capture.read()
            if not ok:
                break
            writer.write(frame)
    finally:
        writer.release()
        capture.release()

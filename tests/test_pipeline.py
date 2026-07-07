from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from core.config import AppConfig, DatabaseConfig, OutputConfig, VideoConfig
from core.models import FaceDetection, Frame, TrackedFace
from core.pipeline import FaceVideoPipeline
from core.storage import SQLiteStore


class FakeAnalyzer:
    """模拟人脸分析器，仅在指定帧返回固定的人脸检测结果。"""

    def __init__(self) -> None:
        """初始化调用计数器。"""
        self.calls = 0

    def analyze(self, frame: Frame) -> list[FaceDetection]:
        """根据帧索引决定是否返回伪造的人脸检测。"""
        self.calls += 1
        if frame.index not in {0, 2, 4}:
            return []
        return [
            FaceDetection(
                frame_index=frame.index,
                timestamp=frame.timestamp,
                bbox_xyxy=(20.0, 20.0, 70.0, 80.0),
                confidence=0.9 + frame.index * 0.01,
                embedding=np.array([1.0, 0.0], dtype=np.float32),
            )
        ]


class FakeTracker:
    """模拟跟踪器，将每个检测包装为固定 track_id 的跟踪人脸。"""

    def update(self, detections: list[FaceDetection], image: np.ndarray) -> list[TrackedFace]:
        """为每个检测结果生成 track_id 为 7 的 TrackedFace。"""
        return [TrackedFace(track_id=7, detection=detection) for detection in detections]


class FakeClusterer:
    """模拟聚类器，将所有人脸轨迹分配到同一人。"""

    def assign_person_ids(self, tracks):
        """把输入的所有轨迹 person_id 设为 0。"""
        for track in tracks:
            track.person_id = 0
        return tracks


def test_pipeline_writes_real_timeline_outputs(tmp_path: Path) -> None:
    """验证流水线能生成真实的时间线文件、截图、片段并将视频写入数据库。"""
    video_path = tmp_path / "sample.mp4"
    _write_video(video_path)
    output_root = tmp_path / "outputs"
    config = AppConfig(
        video=VideoConfig(sample_fps=2.0, min_face_size=10),
        output=OutputConfig(root=output_root, write_person_clips=True),
        database=DatabaseConfig(path=tmp_path / "facetimemarker.db"),
    )

    result_path = FaceVideoPipeline(
        config,
        analyzer=FakeAnalyzer(),
        tracker=FakeTracker(),
        clusterer=FakeClusterer(),
        progress_factory=None,
    ).run(video_path)

    # 校验时间线文件路径与内容
    assert result_path == output_root / "sample" / "timeline.json"
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["people_count"] == 1
    assert payload["people"][0]["label"] == "person_001"
    assert payload["people"][0]["global_person_id"] == "global_person_000001"
    assert payload["people"][0]["track_ids"] == [7]
    assert payload["people"][0]["representative_timestamp"] == 1.0
    assert payload["people"][0]["representative_frame_index"] == 4
    assert payload["tracks"][0]["representative_timestamp"] == 1.0
    assert payload["tracks"][0]["representative_frame_index"] == 4
    assert len(payload["tracks"][0]["detections"]) == 3
    assert payload["persons"]["0"][0]["track_ids"] == [7]

    # 校验代表脸截图、视频片段、CSV 与全局索引文件均已生成
    crop_path = Path(payload["people"][0]["representative_face_path"])
    clip_path = Path(payload["persons"]["0"][0]["clip_path"])
    assert crop_path.exists()
    assert clip_path.exists()
    assert (output_root / "sample" / "timeline.csv").exists()
    assert (output_root / "people_index.json").exists()
    store = SQLiteStore(tmp_path / "facetimemarker.db")
    video = store.list_videos()[0]
    assert video["title"] == "sample"
    people = store.list_people(video["id"])
    tracks = [track for track in store.list_tracks(video["id"]) if track["track_id"] == 7]
    face_crops = store.list_face_crops(video["id"], person_id=0)
    assert people[0]["representative_timestamp"] == 1.0
    assert people[0]["representative_frame_index"] == 4
    assert tracks[0]["representative_timestamp"] == 1.0
    assert tracks[0]["representative_frame_index"] == 4
    assert any(item["timestamp"] == 1.0 and item["frame_index"] == 4 for item in face_crops)
    assert len(store.list_track_detections(video["id"], track_id=7)) == 3


def test_pipeline_reuses_stage_cache_without_rerunning_analyzer(tmp_path: Path) -> None:
    """验证流水线在缓存命中时复用检测与跟踪结果，不再重复调用分析器。"""
    video_path = tmp_path / "sample.mp4"
    _write_video(video_path)
    output_root = tmp_path / "outputs"
    config = AppConfig(
        video=VideoConfig(sample_fps=2.0, min_face_size=10),
        output=OutputConfig(root=output_root, write_person_clips=False),
        database=DatabaseConfig(path=tmp_path / "facetimemarker.db"),
    )

    # 首次运行：应调用分析器并生成阶段缓存
    first_analyzer = FakeAnalyzer()
    pipeline = FaceVideoPipeline(
        config,
        analyzer=first_analyzer,
        tracker=FakeTracker(),
        clusterer=FakeClusterer(),
        progress_factory=None,
    )
    result_path = pipeline.run(video_path)

    cache_files = sorted((output_root / "sample" / ".cache").glob("*.json"))
    assert any(path.name.endswith(".detections.json") for path in cache_files)
    assert any(path.name.endswith(".tracks.json") for path in cache_files)
    assert first_analyzer.calls > 0

    # 删除最终时间线标记，但保留阶段缓存，模拟重新运行
    result_path.unlink()
    for marker in (output_root / "sample" / ".cache").glob("*.timeline.json"):
        marker.unlink()

    # 第二次运行：分析器不应被再次调用
    second_analyzer = FakeAnalyzer()
    FaceVideoPipeline(
        config,
        analyzer=second_analyzer,
        tracker=FakeTracker(),
        clusterer=FakeClusterer(),
        progress_factory=None,
    ).run(video_path)

    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["diagnostics"]["cache_hit"] is True
    assert second_analyzer.calls == 0


def _write_video(path: Path) -> None:
    """辅助函数：生成一段 6 帧的 100x100 测试 MP4 视频。"""
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        4.0,
        (100, 100),
    )
    try:
        for index in range(6):
            frame = np.zeros((100, 100, 3), dtype=np.uint8)
            frame[:, :] = (index * 20, 50, 100)
            writer.write(frame)
    finally:
        writer.release()

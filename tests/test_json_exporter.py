import json
from pathlib import Path

from adapters.exporters.json_exporter import JsonTimelineExporter
from core.config import AppConfig
from core.models import VideoInfo


def test_dry_run_export_serializes_paths(tmp_path: Path) -> None:
    """验证 JsonTimelineExporter 的 dry run 导出能正确序列化视频路径与配置。"""
    video = VideoInfo(
        path=Path("data/example.mp4"),
        fps=25.0,
        frame_count=250,
        width=1920,
        height=1080,
    )

    output = JsonTimelineExporter(tmp_path).write_dry_run(video, AppConfig())
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload["video"]["path"] == "data/example.mp4"
    assert payload["video"]["fps"] == 25.0
    assert payload["config"]["视频"]["采样帧率"] == 2.0

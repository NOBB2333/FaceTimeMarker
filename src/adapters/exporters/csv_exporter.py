from __future__ import annotations

import csv
from pathlib import Path

from core.models import AnalysisResult


class CsvTimelineExporter:
    """人物时间轴 CSV 导出器。"""

    def __init__(self, output_dir: Path) -> None:
        """初始化 CSV 输出目录。"""
        self.output_dir = output_dir

    def write(self, result: AnalysisResult) -> Path:
        """将分析结果写入 timeline.csv 并返回文件路径。"""
        path = self.output_dir / "timeline.csv"
        labels_by_person_id = {person.person_id: person.label for person in result.people}
        global_ids_by_person_id = {
            person.person_id: person.global_person_id for person in result.people
        }
        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    "person_id",
                    "label",
                    "global_person_id",
                    "start",
                    "end",
                    "duration",
                    "detection_count",
                    "track_ids",
                    "clip_path",
                ]
            )
            for person_id, segments in result.persons.items():
                for segment in segments:
                    writer.writerow(
                        [
                            person_id,
                            labels_by_person_id.get(person_id, f"person_{person_id + 1:03d}"),
                            global_ids_by_person_id.get(person_id) or "",
                            f"{segment.start:.3f}",
                            f"{segment.end:.3f}",
                            f"{segment.end - segment.start:.3f}",
                            segment.detection_count,
                            " ".join(str(track_id) for track_id in segment.track_ids),
                            str(segment.clip_path) if segment.clip_path is not None else "",
                        ]
                    )
        return path

from __future__ import annotations

from collections import defaultdict

import numpy as np

from core.models import FaceTrack, PersonSummary, TimelineSegment


class TimelineBuilder:
    """根据人脸轨迹构建人物时间轴。"""

    def __init__(
        self,
        merge_gap_seconds: float = 1.0,
        min_segment_duration: float = 0.0,
    ) -> None:
        """初始化时间轴构建器。"""
        self.merge_gap_seconds = merge_gap_seconds
        self.min_segment_duration = min_segment_duration

    def build(self, tracks: list[FaceTrack]) -> dict[int, list[TimelineSegment]]:
        """把每条轨迹转换为时间轴片段并按人物 ID 分组、合并。"""
        persons: dict[int, list[TimelineSegment]] = defaultdict(list)
        for track in tracks:
            if track.person_id is None or not track.detections:
                continue
            start = track.start
            # 保证即使单帧轨迹也有一个最小时长
            end = max(track.end, start + self.min_segment_duration)
            persons[track.person_id].append(
                TimelineSegment(
                    person_id=track.person_id,
                    start=start,
                    end=end,
                    track_ids=(track.track_id,),
                    detection_count=len(track.detections),
                    clip_path=None,
                )
            )

        return {
            person_id: _merge_segments(
                sorted(segments, key=lambda segment: segment.start),
                max_gap_seconds=self.merge_gap_seconds,
            )
            for person_id, segments in sorted(persons.items())
        }

    def build_people(
        self,
        persons: dict[int, list[TimelineSegment]],
        tracks: list[FaceTrack],
    ) -> list[PersonSummary]:
        """根据时间轴片段和轨迹汇总出每个人物的摘要信息。"""
        tracks_by_person: dict[int, list[FaceTrack]] = defaultdict(list)
        for track in tracks:
            if track.person_id is not None:
                tracks_by_person[track.person_id].append(track)

        people: list[PersonSummary] = []
        for person_id, segments in sorted(persons.items()):
            person_tracks = sorted(tracks_by_person[person_id], key=lambda track: track.track_id)
            embeddings = [track.embedding for track in person_tracks if track.embedding is not None]
            representative = _best_face_track(person_tracks)
            people.append(
                PersonSummary(
                    person_id=person_id,
                    label=f"person_{person_id + 1:03d}",
                    track_ids=tuple(track.track_id for track in person_tracks),
                    appearances=len(segments),
                    total_duration=sum(segment.end - segment.start for segment in segments),
                    detection_count=sum(segment.detection_count for segment in segments),
                    representative_face_path=(
                        representative.representative_face_path if representative is not None else None
                    ),
                    representative_timestamp=(
                        representative.representative_detection.timestamp
                        if representative is not None and representative.representative_detection is not None
                        else None
                    ),
                    representative_frame_index=(
                        representative.representative_detection.frame_index
                        if representative is not None and representative.representative_detection is not None
                        else None
                    ),
                    embedding=_mean_embedding(embeddings),
                )
            )
        return people


def _merge_segments(
    segments: list[TimelineSegment],
    max_gap_seconds: float,
) -> list[TimelineSegment]:
    """合并时间间隔不超过 max_gap_seconds 的相邻片段。"""
    if not segments:
        return []

    merged: list[TimelineSegment] = [segments[0]]
    for segment in segments[1:]:
        previous = merged[-1]
        # 若当前片段与上一片段间隔足够小，则合并时间范围与 track_ids
        if segment.start <= previous.end + max_gap_seconds:
            merged[-1] = TimelineSegment(
                person_id=previous.person_id,
                start=previous.start,
                end=max(previous.end, segment.end),
                track_ids=tuple(sorted({*previous.track_ids, *segment.track_ids})),
                detection_count=previous.detection_count + segment.detection_count,
                clip_path=None,
            )
            continue
        merged.append(segment)
    return merged


def _best_face_track(tracks: list[FaceTrack]) -> FaceTrack | None:
    """从轨迹中选择置信度最高的代表人脸。"""
    return max(
        (track for track in tracks if track.representative_face_path is not None),
        key=lambda track: (
            track.representative_detection.confidence
            if track.representative_detection is not None
            else 0.0
        ),
        default=None,
    )


def _mean_embedding(embeddings: list[np.ndarray]) -> np.ndarray | None:
    """计算多个人脸 embedding 的平均并归一化。"""
    if not embeddings:
        return None
    mean = np.mean(np.vstack(embeddings), axis=0)
    norm = np.linalg.norm(mean)
    if norm <= 0:
        return mean.astype(np.float32)
    return (mean / norm).astype(np.float32)

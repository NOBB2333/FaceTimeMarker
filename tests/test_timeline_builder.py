import numpy as np

from core.models import FaceDetection, FaceTrack
from core.timeline.builder import TimelineBuilder
from core.timeline.context import AppearanceSpan, build_person_context_segments


def test_timeline_builder_merges_close_segments_and_counts_detections() -> None:
    """验证 TimelineBuilder 会合并间隔较小的片段，并正确统计检测数量。"""
    tracks = [
        FaceTrack(
            track_id=1,
            detections=[
                FaceDetection(0, 0.0, (0, 0, 10, 10), 0.9, embedding=np.array([1.0, 0.0])),
            ],
            person_id=0,
        ),
        FaceTrack(
            track_id=2,
            detections=[
                FaceDetection(2, 0.7, (0, 0, 10, 10), 0.9, embedding=np.array([1.0, 0.0])),
            ],
            person_id=0,
        ),
    ]

    # 设置合并间隔大于两帧之间的时间差，使它们被合并为一段
    builder = TimelineBuilder(merge_gap_seconds=0.5, min_segment_duration=0.25)
    persons = builder.build(tracks)
    people = builder.build_people(persons, tracks)

    assert len(persons[0]) == 1
    assert persons[0][0].track_ids == (1, 2)
    assert persons[0][0].detection_count == 2
    assert people[0].detection_count == 2


def test_context_segments_group_dense_person_activity() -> None:
    """验证人物频繁出现时会被合并成一个更大的上下文片段。"""
    spans = [
        AppearanceSpan(0, 10.0, 14.0, track_ids=(1,), detection_count=4, segment_id=101),
        AppearanceSpan(0, 28.0, 33.0, track_ids=(2,), detection_count=5, segment_id=102),
        AppearanceSpan(0, 48.0, 54.0, track_ids=(3,), detection_count=6, segment_id=103),
        AppearanceSpan(0, 180.0, 183.0, track_ids=(4,), detection_count=3, segment_id=104),
    ]

    context_segments = build_person_context_segments(
        spans,
        video_duration=240.0,
        padding_seconds=8.0,
        max_gap_seconds=18.0,
        min_presence_ratio=0.12,
        min_source_segments=2,
    )

    assert len(context_segments) == 2
    dense = context_segments[0]
    assert dense.kind == "dense"
    assert dense.start == 2.0
    assert dense.end == 62.0
    assert dense.source_segment_count == 3
    assert dense.source_segment_ids == (101, 102, 103)
    assert dense.track_ids == (1, 2, 3)
    assert dense.detection_count == 15
    assert dense.presence_ratio >= 0.12

    sparse = context_segments[1]
    assert sparse.kind == "context"
    assert sparse.source_segment_count == 1


def test_context_segments_keep_people_separated() -> None:
    """验证直接传入多个人物片段时，不会跨人物合并。"""
    spans = [
        AppearanceSpan(0, 10.0, 14.0, track_ids=(1,), detection_count=4),
        AppearanceSpan(1, 12.0, 16.0, track_ids=(2,), detection_count=4),
        AppearanceSpan(0, 24.0, 28.0, track_ids=(3,), detection_count=4),
        AppearanceSpan(1, 26.0, 30.0, track_ids=(4,), detection_count=4),
    ]

    context_segments = build_person_context_segments(
        spans,
        video_duration=80.0,
        padding_seconds=4.0,
        max_gap_seconds=20.0,
        min_presence_ratio=0.1,
        min_source_segments=2,
    )

    assert len(context_segments) == 2
    assert [segment.person_id for segment in context_segments] == [0, 1]
    assert [segment.track_ids for segment in context_segments] == [(1, 3), (2, 4)]

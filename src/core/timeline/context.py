from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

from core.models import TimelineSegment


@dataclass(frozen=True)
class AppearanceSpan:
    """一个人物的原始出现片段，用于计算更大的上下文片段。"""

    person_id: int
    start: float
    end: float
    track_ids: tuple[int, ...] = ()
    detection_count: int = 0
    segment_id: int | None = None


@dataclass(frozen=True)
class PersonContextSegment:
    """人物活跃上下文片段，比精确出现片段更适合整段观看。"""

    person_id: int
    start: float
    end: float
    source_segment_count: int
    source_segment_ids: tuple[int, ...]
    track_ids: tuple[int, ...]
    detection_count: int
    appearance_duration: float
    presence_ratio: float
    score: float
    kind: str


def timeline_segments_to_appearance_spans(
    segments: Iterable[TimelineSegment],
) -> list[AppearanceSpan]:
    """把现有 TimelineSegment 转成上下文片段算法使用的输入。"""
    return [
        AppearanceSpan(
            person_id=segment.person_id,
            start=segment.start,
            end=segment.end,
            track_ids=segment.track_ids,
            detection_count=segment.detection_count,
        )
        for segment in segments
    ]


def build_person_context_segments(
    appearances: Iterable[AppearanceSpan],
    video_duration: float,
    padding_seconds: float = 12.0,
    max_gap_seconds: float = 45.0,
    min_presence_ratio: float = 0.08,
    min_source_segments: int = 2,
) -> list[PersonContextSegment]:
    """根据人物出现频率，把精确出现片段合并成更大的上下文观看片段。

    算法只依赖时间轴，不做剧情语义识别：
    1. 先给每个出现片段加前后缓冲，保留对话和动作上下文；
    2. 相邻缓冲片段间隔不大时合并；
    3. 若合并后的片段中人物出现密度达到阈值，标记为 dense。
    """
    if padding_seconds < 0:
        raise ValueError("padding_seconds must be >= 0")
    if max_gap_seconds < 0:
        raise ValueError("max_gap_seconds must be >= 0")
    if not 0 <= min_presence_ratio <= 1:
        raise ValueError("min_presence_ratio must be between 0 and 1")
    if min_source_segments < 1:
        raise ValueError("min_source_segments must be >= 1")

    spans = _normalise_appearances(appearances)
    grouped: dict[int, list[AppearanceSpan]] = {}
    for span in spans:
        grouped.setdefault(span.person_id, []).append(span)

    context_segments: list[PersonContextSegment] = []
    for person_spans in grouped.values():
        context_segments.extend(
            _build_context_segments_for_person(
                person_spans,
                video_duration=video_duration,
                padding_seconds=padding_seconds,
                max_gap_seconds=max_gap_seconds,
                min_presence_ratio=min_presence_ratio,
                min_source_segments=min_source_segments,
            )
        )
    return sorted(context_segments, key=lambda segment: (segment.person_id, segment.start))


def _build_context_segments_for_person(
    spans: list[AppearanceSpan],
    video_duration: float,
    padding_seconds: float,
    max_gap_seconds: float,
    min_presence_ratio: float,
    min_source_segments: int,
) -> list[PersonContextSegment]:
    """为单个人物构造上下文片段。"""
    if not spans:
        return []

    upper_bound = max(video_duration, max(span.end for span in spans))
    groups: list[list[AppearanceSpan]] = []
    current: list[AppearanceSpan] = [spans[0]]

    for span in spans[1:]:
        _, current_end = _expanded_bounds(current, padding_seconds, upper_bound)
        next_start, _ = _expanded_bounds([span], padding_seconds, upper_bound)
        candidate = [*current, span]
        candidate_start, candidate_end = _expanded_bounds(
            candidate,
            padding_seconds,
            upper_bound,
        )
        gap = max(next_start - current_end, 0.0)
        candidate_ratio = _presence_ratio(candidate, candidate_start, candidate_end)
        dense_enough = (
            len(candidate) >= min_source_segments and candidate_ratio >= min_presence_ratio
        )

        if gap <= max_gap_seconds or dense_enough:
            current = candidate
            continue

        groups.append(current)
        current = [span]

    groups.append(current)
    return [
        _context_segment_from_group(
            group,
            padding_seconds=padding_seconds,
            upper_bound=upper_bound,
            min_presence_ratio=min_presence_ratio,
            min_source_segments=min_source_segments,
        )
        for group in groups
    ]


def _normalise_appearances(appearances: Iterable[AppearanceSpan]) -> list[AppearanceSpan]:
    """过滤无效片段并按时间排序。"""
    spans = [
        AppearanceSpan(
            person_id=span.person_id,
            start=max(float(span.start), 0.0),
            end=max(float(span.end), float(span.start)),
            track_ids=tuple(sorted(set(span.track_ids))),
            detection_count=max(int(span.detection_count), 0),
            segment_id=span.segment_id,
        )
        for span in appearances
        if span.end > span.start
    ]
    return sorted(spans, key=lambda span: (span.start, span.end, span.person_id))


def _expanded_bounds(
    group: list[AppearanceSpan],
    padding_seconds: float,
    upper_bound: float,
) -> tuple[float, float]:
    """返回一组片段加上下文缓冲后的范围。"""
    start = max(min(span.start for span in group) - padding_seconds, 0.0)
    end = min(max(span.end for span in group) + padding_seconds, upper_bound)
    return start, max(end, start)


def _context_segment_from_group(
    group: list[AppearanceSpan],
    padding_seconds: float,
    upper_bound: float,
    min_presence_ratio: float,
    min_source_segments: int,
) -> PersonContextSegment:
    """把一组原始出现片段转换为上下文片段。"""
    start, end = _expanded_bounds(group, padding_seconds, upper_bound)
    appearance_duration = sum(span.end - span.start for span in group)
    duration = max(end - start, 0.000001)
    presence_ratio = appearance_duration / duration
    source_segment_ids = tuple(
        int(span.segment_id) for span in group if span.segment_id is not None
    )
    track_ids = tuple(sorted({track_id for span in group for track_id in span.track_ids}))
    detection_count = sum(span.detection_count for span in group)
    source_segment_count = len(group)
    kind = (
        "dense"
        if source_segment_count >= min_source_segments and presence_ratio >= min_presence_ratio
        else "context"
    )
    score = presence_ratio * math.log1p(source_segment_count)

    return PersonContextSegment(
        person_id=group[0].person_id,
        start=start,
        end=end,
        source_segment_count=source_segment_count,
        source_segment_ids=source_segment_ids,
        track_ids=track_ids,
        detection_count=detection_count,
        appearance_duration=appearance_duration,
        presence_ratio=presence_ratio,
        score=score,
        kind=kind,
    )


def _presence_ratio(group: list[AppearanceSpan], start: float, end: float) -> float:
    """计算人物精确出现时长占上下文片段时长的比例。"""
    duration = max(end - start, 0.000001)
    appearance_duration = sum(span.end - span.start for span in group)
    return appearance_duration / duration

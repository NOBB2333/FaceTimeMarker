from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

import numpy as np
from tqdm import tqdm

from adapters.exporters.clip_exporter import PersonClipExporter
from adapters.exporters.csv_exporter import CsvTimelineExporter
from adapters.exporters.face_crop_exporter import FaceCropExporter
from adapters.exporters.json_exporter import JsonTimelineExporter
from adapters.face.base import FaceAnalyzer
from adapters.face.insightface_analyzer import InsightFaceAnalyzer
from adapters.identity.store import IdentityStore
from adapters.tracking.base import FaceTracker
from adapters.tracking.boxmot_botsort import BoxmotBotSortTracker
from adapters.tracking.supervision_bytetrack import SupervisionByteTracker
from adapters.video.reader import iter_sampled_frames, probe_video
from core.cache import (
    DetectionFrameCache,
    StageCacheStats,
    read_detection_cache,
    read_track_cache,
    write_detection_cache,
    write_track_cache,
)
from core.clustering.base import FaceClusterer
from core.clustering.dbscan_clusterer import DbscanFaceClusterer
from core.clustering.hdbscan_clusterer import HdbscanFaceClusterer
from core.config import AppConfig
from core.models import (
    AnalysisDiagnostics,
    AnalysisResult,
    FaceDetection,
    FaceTrack,
    Frame,
    TimelineSegment,
    VideoInfo,
)
from core.storage import ResultStore
from core.timeline.builder import TimelineBuilder


class ProgressFactory(Protocol):
    """进度条工厂协议，用于注入自定义进度显示。"""

    # 将可迭代对象包装为带进度显示的可迭代对象
    def __call__(self, iterable, **kwargs): ...


class PipelineCancelled(Exception):
    """分析任务被外部请求取消。"""


class FaceVideoPipeline:
    """人脸视频分析主流程。"""

    def __init__(
        self,
        config: AppConfig,
        analyzer: FaceAnalyzer | None = None,
        tracker: FaceTracker | None = None,
        clusterer: FaceClusterer | None = None,
        progress_factory: ProgressFactory | None = tqdm,
        should_cancel: Callable[[], bool] | None = None,
    ) -> None:
        """初始化流水线，可注入自定义分析器、跟踪器、聚类器和进度条。"""
        self.config = config
        self.analyzer = analyzer
        self.tracker = tracker
        self.clusterer = clusterer
        self.progress_factory = progress_factory
        self.should_cancel = should_cancel

    def run(
        self,
        video_path: Path,
        dry_run: bool = False,
        preset: str | None = None,
        use_cache: bool = True,
        output_name: str | None = None,
    ) -> Path:
        """执行视频分析主流程，返回结果文件或输出目录路径。"""
        video_info = probe_video(video_path)
        output_dir = _analysis_output_dir(self.config.output.root, output_name or video_path.stem, video_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        self._raise_if_canceled()

        # dry_run 只验证配置和视频读取，不运行视觉推理
        if dry_run:
            return JsonTimelineExporter(output_dir).write_dry_run(video_info, self.config)

        cache_key = _analysis_cache_key(video_info, self.config, preset)
        cache_dir = output_dir / ".cache"
        cache_path = cache_dir / f"{cache_key}.timeline.json"
        detection_cache_path = cache_dir / f"{cache_key}.detections.json"
        track_cache_path = cache_dir / f"{cache_key}.tracks.json"
        result_path = output_dir / "timeline.json"
        # 如果结果与缓存标记都已存在，则直接返回缓存结果
        if use_cache and result_path.exists() and cache_path.exists():
            return result_path

        started_at = time.perf_counter()
        cache_hit = False
        stage_stats = StageCacheStats()

        clusterer = self.clusterer or _build_clusterer(self.config)
        self._raise_if_canceled()

        # 优先尝试读取 track 缓存；若命中则跳过检测与跟踪阶段
        track_cache = read_track_cache(track_cache_path) if use_cache else None
        representative_frames_by_track: dict[int, Frame] = {}
        if track_cache is not None:
            tracks, stage_stats = track_cache
            cache_hit = True
        else:
            detection_cache = read_detection_cache(detection_cache_path) if use_cache else None
            if detection_cache is not None:
                detection_frames, stage_stats = detection_cache
                cache_hit = True
            else:
                analyzer = self.analyzer or _build_analyzer(self.config)
                detection_frames, stage_stats = self._analyze_frames(
                    video_path,
                    video_info,
                    analyzer,
                )
                self._raise_if_canceled()
                if use_cache:
                    write_detection_cache(detection_cache_path, detection_frames, stage_stats)

            self._raise_if_canceled()
            tracker = self.tracker or _build_tracker(
                self.config,
                frame_rate=max(round(video_info.fps), 1),
            )
            tracks, representative_frames_by_track = self._track_detections(
                video_path,
                detection_frames,
                tracker,
            )
            self._raise_if_canceled()
            tracks = [
                _finalize_track(track)
                for track in sorted(tracks, key=lambda candidate: candidate.track_id)
            ]
            if use_cache:
                write_track_cache(track_cache_path, tracks, stage_stats)

        # 过滤掉太短、未达到最小连续帧数的轨迹
        tracks = [
            track
            for track in tracks
            if len(track.detections) >= self.config.tracking.minimum_consecutive_frames
        ]

        self._raise_if_canceled()
        clusterer.assign_person_ids(tracks)

        if self.config.output.write_face_crops and representative_frames_by_track:
            _write_representative_faces(output_dir, tracks, representative_frames_by_track)
            # 代表人脸路径更新后，重新写入 track 缓存以保留最新状态
            if use_cache and track_cache is None:
                write_track_cache(track_cache_path, tracks, stage_stats)

        timeline_builder = TimelineBuilder(
            merge_gap_seconds=self.config.timeline.merge_gap_seconds,
            min_segment_duration=1.0 / self.config.video.sample_fps,
        )
        persons = timeline_builder.build(tracks)
        if self.config.output.write_person_clips:
            _write_person_clips(output_dir, video_info, persons)
        people = timeline_builder.build_people(persons, tracks)

        self._raise_if_canceled()
        # 若启用跨视频人物匹配，则更新全局人物库
        if self.config.identity_store.enabled:
            identity_store = IdentityStore.load(
                self.config.identity_store_path(),
                match_threshold=self.config.identity_store.match_threshold,
            )
            people = identity_store.assign(people, video_info)
            identity_store.save()

        elapsed_seconds = time.perf_counter() - started_at
        diagnostics = AnalysisDiagnostics(
            sampled_frames=stage_stats.sampled_frames,
            raw_faces=stage_stats.raw_faces,
            kept_faces=stage_stats.kept_faces,
            filtered_small_faces=max(stage_stats.raw_faces - stage_stats.kept_faces, 0),
            tracks=len(tracks),
            people=len(people),
            elapsed_seconds=elapsed_seconds,
            frames_per_second=(
                stage_stats.sampled_frames / elapsed_seconds if elapsed_seconds > 0 else 0.0
            ),
            average_face_width=stage_stats.average_face_width,
            average_face_height=stage_stats.average_face_height,
            preset=preset,
            cache_hit=cache_hit,
        )
        result = AnalysisResult(
            video=video_info,
            people=people,
            persons=persons,
            tracks=tracks,
            diagnostics=diagnostics,
        )

        written: list[Path] = []
        self._raise_if_canceled()
        if self.config.output.write_json:
            written.append(JsonTimelineExporter(output_dir).write(result))
        if self.config.output.write_csv:
            written.append(CsvTimelineExporter(output_dir).write(result))

        if not written:
            return output_dir
        self._raise_if_canceled()
        _write_cache_marker(cache_path)
        ResultStore(self.config.database.path, url=self.config.database.url).import_timeline(
            written[0],
            original_filename=video_path.name,
            source_path=str(video_path),
            source_directory=str(video_path.parent),
        )
        return written[0]

    def _raise_if_canceled(self) -> None:
        """在耗时阶段之间检查外部取消请求。"""
        if self.should_cancel is not None and self.should_cancel():
            raise PipelineCancelled("analysis canceled")

    def _analyze_frames(
        self,
        video_path: Path,
        video_info: VideoInfo,
        analyzer: FaceAnalyzer,
    ) -> tuple[list[DetectionFrameCache], StageCacheStats]:
        """逐帧运行人脸检测和 embedding，并返回可复用的阶段缓存。"""
        sampled_frames = 0
        raw_faces = 0
        kept_faces = 0
        face_width_sum = 0.0
        face_height_sum = 0.0
        face_size_count = 0
        detection_frames: list[DetectionFrameCache] = []

        frames = iter_sampled_frames(video_path, self.config.video.sample_fps)
        total_frames = _estimated_sampled_frame_count(
            video_info.frame_count,
            video_info.fps,
            self.config.video.sample_fps,
        )
        if self.progress_factory is not None:
            frames = self.progress_factory(
                frames,
                total=total_frames,
                desc="analyze",
                unit="frame",
            )

        for frame in frames:
            self._raise_if_canceled()
            sampled_frames += 1
            detections = analyzer.analyze(frame)
            raw_faces += len(detections)
            for detection in detections:
                width, height = _face_size(detection)
                face_width_sum += width
                face_height_sum += height
                face_size_count += 1
            detections = _filter_detections(
                detections,
                min_face_size=self.config.video.min_face_size,
            )
            kept_faces += len(detections)
            detection_frames.append(
                DetectionFrameCache(
                    frame_index=frame.index,
                    timestamp=frame.timestamp,
                    detections=detections,
                )
            )

        return detection_frames, StageCacheStats(
            sampled_frames=sampled_frames,
            raw_faces=raw_faces,
            kept_faces=kept_faces,
            face_width_sum=face_width_sum,
            face_height_sum=face_height_sum,
            face_size_count=face_size_count,
        )

    def _track_detections(
        self,
        video_path: Path,
        detection_frames: list[DetectionFrameCache],
        tracker: FaceTracker,
    ) -> tuple[list[FaceTrack], dict[int, Frame]]:
        """基于缓存检测结果重新生成 track。"""
        tracks_by_id: dict[int, FaceTrack] = {}
        representative_frames_by_track: dict[int, Frame] = {}
        # 重新读取视频帧图像，用于跟踪器输入与代表帧选择
        frame_images = {
            frame.index: frame.image
            for frame in iter_sampled_frames(video_path, self.config.video.sample_fps)
        }
        empty_image = np.zeros((1, 1, 3), dtype=np.uint8)

        for frame_cache in detection_frames:
            self._raise_if_canceled()
            image = frame_images.get(frame_cache.frame_index, empty_image)
            frame = Frame(
                index=frame_cache.frame_index,
                timestamp=frame_cache.timestamp,
                image=image,
            )
            tracked_faces = tracker.update(frame_cache.detections, image)
            for tracked_face in tracked_faces:
                track = tracks_by_id.setdefault(
                    tracked_face.track_id,
                    FaceTrack(tracked_face.track_id),
                )
                track.detections.append(tracked_face.detection)
                if _is_better_representative(
                    tracked_face.detection,
                    track.representative_detection,
                ):
                    track.representative_detection = tracked_face.detection
                    representative_frames_by_track[track.track_id] = frame

        return list(tracks_by_id.values()), representative_frames_by_track


def _build_analyzer(config: AppConfig) -> FaceAnalyzer:
    """根据配置构建人脸分析器。"""
    if config.face.provider != "insightface":
        raise ValueError(f"Unsupported face provider: {config.face.provider}")
    return InsightFaceAnalyzer(config.face)


def _build_tracker(config: AppConfig, frame_rate: int) -> FaceTracker:
    """根据配置构建人脸跟踪器。"""
    if config.tracking.provider == "boxmot_botsort":
        return BoxmotBotSortTracker(config.tracking)
    if config.tracking.provider == "supervision_bytetrack":
        return SupervisionByteTracker(config.tracking, frame_rate=frame_rate)
    raise ValueError(f"Unsupported tracking provider: {config.tracking.provider}")


def _build_clusterer(config: AppConfig) -> FaceClusterer:
    """根据配置构建人脸聚类器。"""
    if config.clustering.provider == "hdbscan":
        return HdbscanFaceClusterer(config.clustering)
    if config.clustering.provider == "dbscan":
        return DbscanFaceClusterer(config.clustering)
    raise ValueError(f"Unsupported clustering provider: {config.clustering.provider}")


def _filter_detections(
    detections: list[FaceDetection],
    min_face_size: int,
) -> list[FaceDetection]:
    """按最小人脸尺寸过滤检测结果。"""
    filtered: list[FaceDetection] = []
    for detection in detections:
        x1, y1, x2, y2 = detection.bbox_xyxy
        if x2 - x1 < min_face_size or y2 - y1 < min_face_size:
            continue
        filtered.append(detection)
    return filtered


def _finalize_track(track: FaceTrack) -> FaceTrack:
    """计算轨迹的平均 embedding 并归一化，作为该轨迹的人脸特征。"""
    embeddings = [
        detection.embedding for detection in track.detections if detection.embedding is not None
    ]
    if embeddings:
        mean = np.mean(np.vstack(embeddings), axis=0)
        norm = np.linalg.norm(mean)
        track.embedding = (mean / norm).astype(np.float32) if norm > 0 else mean.astype(np.float32)
    return track


def _is_better_representative(
    candidate: FaceDetection,
    current: FaceDetection | None,
) -> bool:
    """判断 candidate 是否比 current 更适合作为代表人脸。"""
    if current is None:
        return True
    return _face_quality(candidate) > _face_quality(current)


def _face_quality(detection: FaceDetection) -> tuple[float, float]:
    """计算人脸质量：优先置信度，其次人脸面积。"""
    x1, y1, x2, y2 = detection.bbox_xyxy
    area = max(x2 - x1, 0.0) * max(y2 - y1, 0.0)
    return detection.confidence, area


def _face_size(detection: FaceDetection) -> tuple[float, float]:
    """返回检测框宽高。"""
    x1, y1, x2, y2 = detection.bbox_xyxy
    return max(x2 - x1, 0.0), max(y2 - y1, 0.0)


def _write_representative_faces(
    output_dir: Path,
    tracks: list[FaceTrack],
    frames_by_track: dict[int, Frame],
) -> None:
    """为每个人物选择质量最高的代表人脸并写入截图，同时回写路径到轨迹中。"""
    exporter = FaceCropExporter(output_dir)
    best_track_by_person: dict[int, FaceTrack] = {}
    # 先为每个人物挑选质量最高的轨迹
    for track in tracks:
        if track.person_id is None or track.representative_detection is None:
            continue
        current = best_track_by_person.get(track.person_id)
        if current is None:
            best_track_by_person[track.person_id] = track
            continue
        if current.representative_detection is None:
            best_track_by_person[track.person_id] = track
            continue
        if _face_quality(track.representative_detection) > _face_quality(
            current.representative_detection
        ):
            best_track_by_person[track.person_id] = track

    # 写出截图并把路径同步到该人物的所有轨迹
    for person_id, track in best_track_by_person.items():
        frame = frames_by_track.get(track.track_id)
        if frame is None or track.representative_detection is None:
            continue
        path = exporter.write(frame, track.representative_detection, person_id=person_id)
        for person_track in tracks:
            if person_track.person_id == person_id:
                person_track.representative_face_path = path


def _write_person_clips(
    output_dir: Path,
    video_info: VideoInfo,
    persons: dict[int, list[TimelineSegment]],
) -> None:
    """为每个人物片段生成短视频并更新片段路径。"""
    exporter = PersonClipExporter(output_dir)
    for segments in persons.values():
        for index, segment in enumerate(segments, start=1):
            clip_path = exporter.write(video_info, segment, index)
            segments[index - 1] = type(segment)(
                person_id=segment.person_id,
                start=segment.start,
                end=segment.end,
                track_ids=segment.track_ids,
                detection_count=segment.detection_count,
                clip_path=clip_path,
            )


def _estimated_sampled_frame_count(
    frame_count: int,
    fps: float,
    sample_fps: float,
) -> int | None:
    """估算按 sample_fps 采样后会处理的帧数。"""
    if frame_count <= 0 or fps <= 0 or sample_fps <= 0:
        return None
    step = max(int(round(fps / sample_fps)), 1)
    return (frame_count + step - 1) // step


def _analysis_cache_key(video: VideoInfo, config: AppConfig, preset: str | None) -> str:
    """根据视频元数据和配置生成结果缓存 key。"""
    payload = {
        "video": {
            "path": str(video.path.resolve()),
            "fps": video.fps,
            "frame_count": video.frame_count,
            "width": video.width,
            "height": video.height,
            "mtime": video.path.stat().st_mtime if video.path.exists() else None,
        },
        "preset": preset,
        "config": config.analysis_cache_payload(),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _analysis_output_dir(root: Path, output_name: str, video_path: Path) -> Path:
    """按可读文件名生成输出目录，重名时追加数字后缀。"""
    stem = _safe_output_stem(Path(output_name).stem or video_path.stem)
    base = root / stem
    for index in range(1, 1000):
        candidate = base if index == 1 else root / f"{stem}-{index}"
        if not candidate.exists():
            return candidate
        timeline_path = candidate / "timeline.json"
        if not timeline_path.exists():
            return candidate
        try:
            payload = json.loads(timeline_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if str(payload.get("video", {}).get("path") or "") == str(video_path):
            return candidate
    return root / f"{stem}-{hashlib.sha256(str(video_path).encode('utf-8')).hexdigest()[:8]}"


def _safe_output_stem(name: str) -> str:
    """清理输出目录名，保留用户可读文件名。"""
    cleaned = "".join(
        char if char >= " " and char not in '<>:"/\\|?*' else "_"
        for char in name.strip()
    ).strip(" .")
    return cleaned or "video"


def _write_cache_marker(path: Path) -> None:
    """写入结果缓存标记。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"cached": True}, ensure_ascii=False), encoding="utf-8")

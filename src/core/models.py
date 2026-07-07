from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class VideoInfo:
    """视频基本信息。"""

    path: Path  # 视频文件路径
    fps: float  # 帧率（帧/秒）
    frame_count: int  # 总帧数
    width: int  # 视频宽度（像素）
    height: int  # 视频高度（像素）

    @property
    def duration_seconds(self) -> float:
        """计算视频时长（秒），帧率异常时返回 0。"""
        if self.fps <= 0:
            return 0.0
        return self.frame_count / self.fps


@dataclass(frozen=True)
class Frame:
    """视频中的一帧。"""

    index: int  # 帧序号
    timestamp: float  # 时间戳（秒）
    image: np.ndarray  # 帧图像数据


@dataclass(frozen=True)
class FaceDetection:
    """单帧中检测到的人脸。"""

    frame_index: int  # 所在帧序号
    timestamp: float  # 所在帧时间戳（秒）
    bbox_xyxy: tuple[float, float, float, float]  # 人脸边界框（左上 x, 左上 y, 右下 x, 右下 y）
    confidence: float  # 检测置信度
    embedding: np.ndarray | None = None  # 人脸特征向量
    landmarks: np.ndarray | None = None  # 人脸关键点


@dataclass(frozen=True)
class TrackedFace:
    """带跟踪 ID 的人脸。"""

    track_id: int  # 跟踪器分配的轨迹 ID
    detection: FaceDetection  # 对应的人脸检测


@dataclass
class FaceTrack:
    """同一人脸在视频中的连续轨迹。"""

    track_id: int  # 轨迹 ID
    detections: list[FaceDetection] = field(default_factory=list)  # 轨迹包含的所有检测
    embedding: np.ndarray | None = None  # 轨迹平均特征向量
    person_id: int | None = None  # 聚类后的人物 ID
    representative_detection: FaceDetection | None = None  # 质量最高的人脸检测
    representative_face_path: Path | None = None  # 代表人脸截图保存路径

    @property
    def start(self) -> float:
        """返回轨迹起始时间（秒）。"""
        return min(d.timestamp for d in self.detections)

    @property
    def end(self) -> float:
        """返回轨迹结束时间（秒）。"""
        return max(d.timestamp for d in self.detections)


@dataclass(frozen=True)
class TimelineSegment:
    """人物在某段时间内的出现片段。"""

    person_id: int  # 人物 ID
    start: float  # 片段开始时间（秒）
    end: float  # 片段结束时间（秒）
    track_ids: tuple[int, ...]  # 该片段包含的轨迹 ID 集合
    detection_count: int = 0  # 该片段包含的检测次数
    clip_path: Path | None = None  # 片段视频保存路径


@dataclass(frozen=True)
class PersonSummary:
    """单个人物的汇总信息。"""

    person_id: int  # 本视频内的人物 ID
    label: str  # 人物标签
    track_ids: tuple[int, ...]  # 所属轨迹 ID 集合
    appearances: int  # 出现片段数
    total_duration: float  # 总出现时长（秒）
    detection_count: int = 0  # 总检测次数
    representative_face_path: Path | None = None  # 代表人脸截图路径
    representative_timestamp: float | None = None  # 代表人脸截图所在时间
    representative_frame_index: int | None = None  # 代表人脸截图所在帧
    embedding: np.ndarray | None = None  # 人物平均特征向量
    global_person_id: str | None = None  # 跨视频全局人物 ID


@dataclass(frozen=True)
class AnalysisDiagnostics:
    """一次分析的诊断和性能统计。"""

    sampled_frames: int  # 实际抽样帧数
    raw_faces: int  # 原始检测人脸数
    kept_faces: int  # 过滤后保留人脸数
    filtered_small_faces: int  # 因尺寸过滤掉的人脸数
    tracks: int  # 过滤后轨迹数
    people: int  # 输出人物数
    elapsed_seconds: float  # 总耗时
    frames_per_second: float  # 分析速度：抽样帧/秒
    average_face_width: float  # 原始检测平均人脸宽度
    average_face_height: float  # 原始检测平均人脸高度
    preset: str | None = None  # 使用的预设
    cache_hit: bool = False  # 是否命中缓存


@dataclass(frozen=True)
class AnalysisResult:
    """一次视频分析的完整结果。"""

    video: VideoInfo  # 视频信息
    people: list[PersonSummary]  # 人物汇总列表
    persons: dict[int, list[TimelineSegment]]  # 按人物 ID 分组的时间轴片段
    tracks: list[FaceTrack] = field(default_factory=list)  # 所有人脸轨迹
    diagnostics: AnalysisDiagnostics | None = None  # 分析诊断信息

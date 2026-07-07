from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib


class ChineseAliasModel(BaseModel):
    """支持中文配置键和内部英文属性名的配置基类。"""

    model_config = ConfigDict(populate_by_name=True)


class VideoConfig(ChineseAliasModel):
    """视频处理相关配置。"""

    sample_fps: float = Field(default=2.0, alias="采样帧率", gt=0)
    min_face_size: int = Field(default=32, alias="最小人脸尺寸", ge=1)


class FaceConfig(ChineseAliasModel):
    """人脸检测与特征提取配置。"""

    provider: str = Field(default="insightface", alias="提供方")
    model_name: str = Field(default="buffalo_l", alias="模型名称")
    det_size: tuple[int, int] = Field(default=(640, 640), alias="检测尺寸")
    det_score_threshold: float = Field(default=0.5, alias="检测置信度阈值", ge=0, le=1)
    execution_provider_profile: str = Field(default="auto", alias="执行提供方策略")
    allow_cpu_fallback: bool = Field(default=True, alias="允许CPU降级")
    execution_providers: list[str] = Field(
        default_factory=lambda: ["CPUExecutionProvider"],
        alias="ONNX执行提供方",
    )


class TrackingConfig(ChineseAliasModel):
    """人脸跟踪配置。"""

    provider: str = Field(default="boxmot_botsort", alias="提供方")
    algorithm: str = Field(default="botsort", alias="算法")
    track_activation_threshold: float = Field(default=0.25, alias="轨迹激活阈值", ge=0, le=1)
    lost_track_buffer: int = Field(default=30, alias="丢失轨迹缓冲帧数", ge=1)
    minimum_matching_threshold: float = Field(default=0.8, alias="最小匹配阈值", ge=0, le=1)
    minimum_consecutive_frames: int = Field(default=1, alias="最小连续帧数", ge=1)
    cmc_method: str = Field(default="ecc", alias="相机运动补偿方法")
    proximity_threshold: float = Field(default=0.5, alias="空间接近阈值", ge=0, le=1)
    appearance_threshold: float = Field(default=0.25, alias="外观相似阈值", ge=0, le=1)


class ClusteringConfig(ChineseAliasModel):
    """人脸聚类配置。"""

    provider: str = Field(default="hdbscan", alias="提供方")
    expected_people_count: int | None = Field(default=None, alias="预设人物数量", ge=1)
    eps: float = Field(default=0.45, alias="DBSCAN邻域半径", gt=0)
    min_samples: int = Field(default=3, alias="最小样本数", ge=1)
    min_cluster_size: int = Field(default=3, alias="最小簇大小", ge=2)
    cluster_selection_epsilon: float = Field(default=0.0, alias="簇选择距离", ge=0)


class TimelineConfig(ChineseAliasModel):
    """时间轴构建配置。"""

    merge_gap_seconds: float = Field(default=1.0, alias="合并间隔秒数", ge=0)


class OutputConfig(ChineseAliasModel):
    """输出配置。"""

    root: Path = Field(default=Path("_outputs"), alias="根目录")
    write_json: bool = Field(default=True, alias="写入JSON")
    write_csv: bool = Field(default=True, alias="写入CSV")
    write_face_crops: bool = Field(default=True, alias="保存代表人脸")
    write_person_clips: bool = Field(default=False, alias="保存人物片段")


class SourceMediaConfig(ChineseAliasModel):
    """源媒体管理配置。"""

    copy_source_files: bool = Field(default=False, alias="拷贝源文件")
    upload_file_naming: str = Field(default="original", alias="上传保存命名")


class FrameBoxConfig(ChineseAliasModel):
    """逐帧框存储与播放叠加配置。"""

    write_to_sqlite: bool = Field(default=True, alias="写入SQLite")
    use_for_video_overlay: bool = Field(default=True, alias="播放红框使用逐帧框")
    nearest_frame_tolerance_seconds: float = Field(default=0.8, alias="最近帧容忍秒数", ge=0)
    max_api_rows: int = Field(default=20000, alias="接口最大返回行数", ge=1)


class ReferenceExportConfig(ChineseAliasModel):
    """人物参考图导出配置。"""

    output_subdir: str = Field(default="references", alias="输出子目录")
    frames_per_person: int = Field(default=12, alias="每人导出张数", ge=1)
    sampling_strategy: str = Field(default="best", alias="抽帧策略")
    crop_mode: str = Field(default="full_frame", alias="裁剪模式")
    include_clean_image: bool = Field(default=True, alias="同时导出无框原图")
    include_face_box: bool = Field(default=True, alias="保留人脸框")
    include_identity_label: bool = Field(default=True, alias="写入人物标签")
    face_box_color: str = Field(default="#ffd84d", alias="人脸框颜色")
    box_thickness: int = Field(default=3, alias="框线粗细", ge=1)
    output_format: str = Field(default="jpg", alias="输出格式")
    jpeg_quality: int = Field(default=95, alias="JPEG质量", ge=1, le=100)
    output_size: int | None = Field(default=None, alias="输出长边尺寸", ge=1)
    write_manifest: bool = Field(default=True, alias="写入清单")


class LargeModelConfig(ChineseAliasModel):
    """大模型接口配置。"""

    enabled: bool = Field(default=False, alias="启用")
    provider: str = Field(default="openai", alias="提供方")
    base_url: str = Field(default="https://api.openai.com/v1", alias="接口地址")
    api_key: str = Field(default="", alias="API Key")
    model: str = Field(default="", alias="模型")
    timeout_seconds: float = Field(default=120.0, alias="超时时间秒", gt=0)
    max_retries: int = Field(default=2, alias="最大重试次数", ge=0)
    max_output_tokens: int = Field(default=4096, alias="最大输出Token", ge=1)
    temperature: float | None = Field(default=None, alias="温度", ge=0, le=2)


class ImageGenerationConfig(ChineseAliasModel):
    """图像生成配置。"""

    enabled: bool = Field(default=False, alias="启用")
    model: str = Field(default="", alias="模型")
    action: str = Field(default="auto", alias="动作")
    size: str = Field(default="auto", alias="尺寸")
    quality: str = Field(default="auto", alias="质量")
    output_format: str = Field(default="webp", alias="输出格式")
    background: str = Field(default="auto", alias="背景")
    input_fidelity: str = Field(default="high", alias="输入保真度")
    moderation: str = Field(default="auto", alias="审核强度")
    output_compression: int | None = Field(default=85, alias="输出压缩", ge=0, le=100)
    partial_images: int = Field(default=0, alias="流式预览张数", ge=0, le=3)
    prompt_template: str = Field(default="", alias="提示词模板")


class IdentityStoreConfig(ChineseAliasModel):
    """跨视频人物库配置。"""

    enabled: bool = Field(default=True, alias="启用")
    path: Path | None = Field(default=None, alias="路径")
    match_threshold: float = Field(default=0.55, alias="匹配阈值", ge=0, le=1)


class DatabaseConfig(ChineseAliasModel):
    """本地数据库配置。"""

    path: Path = Field(default=Path("_outputs/facetimemarker.db"), alias="路径")
    url: str | None = Field(default=None, alias="URL")


class AppConfig(ChineseAliasModel):
    """应用顶层配置。"""

    video: VideoConfig = Field(default_factory=VideoConfig, alias="视频")
    face: FaceConfig = Field(default_factory=FaceConfig, alias="人脸")
    tracking: TrackingConfig = Field(default_factory=TrackingConfig, alias="跟踪")
    clustering: ClusteringConfig = Field(default_factory=ClusteringConfig, alias="聚类")
    timeline: TimelineConfig = Field(default_factory=TimelineConfig, alias="时间轴")
    output: OutputConfig = Field(default_factory=OutputConfig, alias="输出")
    source_media: SourceMediaConfig = Field(default_factory=SourceMediaConfig, alias="源媒体")
    frame_boxes: FrameBoxConfig = Field(default_factory=FrameBoxConfig, alias="逐帧框")
    reference_export: ReferenceExportConfig = Field(
        default_factory=ReferenceExportConfig,
        alias="参考图导出",
    )
    large_model: LargeModelConfig = Field(default_factory=LargeModelConfig, alias="大模型")
    image_generation: ImageGenerationConfig = Field(
        default_factory=ImageGenerationConfig,
        alias="图像生成",
    )
    identity_store: IdentityStoreConfig = Field(default_factory=IdentityStoreConfig, alias="人物库")
    database: DatabaseConfig = Field(default_factory=DatabaseConfig, alias="数据库")

    def identity_store_path(self) -> Path:
        """返回人物库文件路径，未配置时使用默认路径。"""
        return self.identity_store.path or self.output.root / "people_index.json"

    def analysis_cache_payload(self) -> dict[str, Any]:
        """返回会影响视频分析结果的配置，避免 API Key 等外部配置污染缓存。"""
        return {
            "视频": self.video.model_dump(mode="json", by_alias=True),
            "人脸": self.face.model_dump(mode="json", by_alias=True),
            "跟踪": self.tracking.model_dump(mode="json", by_alias=True),
            "聚类": self.clustering.model_dump(mode="json", by_alias=True),
            "时间轴": self.timeline.model_dump(mode="json", by_alias=True),
            "输出": self.output.model_dump(mode="json", by_alias=True),
            "源媒体": self.source_media.model_dump(mode="json", by_alias=True),
            "逐帧框": self.frame_boxes.model_dump(mode="json", by_alias=True),
            "人物库": self.identity_store.model_dump(mode="json", by_alias=True),
        }


PRESET_NAMES = ("fast", "balanced", "crowd")


def apply_preset(config: AppConfig, preset: str | None) -> AppConfig:
    """应用分析预设，返回新的配置对象。"""
    if preset is None:
        return config
    if preset not in PRESET_NAMES:
        raise ValueError(f"Unsupported preset: {preset}")

    updated = config.model_copy(deep=True)
    if preset == "fast":
        updated.video.sample_fps = 2.0
        updated.video.min_face_size = 32
        updated.face.det_score_threshold = 0.5
        updated.tracking.minimum_consecutive_frames = 1
    elif preset == "balanced":
        updated.video.sample_fps = 5.0
        updated.video.min_face_size = 24
        updated.face.det_score_threshold = 0.45
        updated.tracking.minimum_consecutive_frames = 2
    elif preset == "crowd":
        updated.video.sample_fps = 8.0
        updated.video.min_face_size = 16
        updated.face.det_score_threshold = 0.4
        updated.tracking.minimum_consecutive_frames = 1
    return updated


def load_config(path: Path | None = None) -> AppConfig:
    """从 TOML 配置文件加载应用配置。"""
    if path is None:
        path = Path("configs/default.toml")
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    raw = _load_toml_with_includes(path)

    return AppConfig.model_validate(raw)


def _load_toml_with_includes(path: Path, seen: set[Path] | None = None) -> dict[str, Any]:
    """加载 TOML，并按顺序合并“包含配置”中的子配置。"""
    resolved = path.resolve()
    if seen is None:
        seen = set()
    if resolved in seen:
        raise ValueError(f"Recursive config include detected: {path}")
    seen.add(resolved)

    with path.open("rb") as file:
        raw: dict[str, Any] = tomllib.load(file)

    includes = raw.pop("包含配置", [])
    if isinstance(includes, str):
        includes = [includes]
    if not isinstance(includes, list):
        raise ValueError("包含配置 must be a string or list of strings")

    merged: dict[str, Any] = {}
    for item in includes:
        if not isinstance(item, str):
            raise ValueError("包含配置 entries must be strings")
        include_path = Path(item)
        if not include_path.is_absolute():
            include_path = path.parent / include_path
        merged = _deep_merge(merged, _load_toml_with_includes(include_path, seen))

    seen.remove(resolved)
    return _deep_merge(merged, raw)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """递归合并配置字典，后者覆盖前者。"""
    merged = dict(base)
    for key, value in override.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = _deep_merge(current, value)
        else:
            merged[key] = value
    return merged

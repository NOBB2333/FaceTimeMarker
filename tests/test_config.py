from pathlib import Path

from core.config import AppConfig, load_config


def test_load_default_config() -> None:
    """验证默认配置文件能被正确加载，且关键配置项符合预期。"""
    config = load_config(Path("configs/default.toml"))

    assert config.face.provider == "insightface"
    assert config.tracking.provider == "boxmot_botsort"
    assert config.tracking.algorithm == "botsort"
    assert config.clustering.provider == "hdbscan"
    assert config.clustering.expected_people_count is None
    assert config.output.root == Path("_outputs")
    assert config.source_media.copy_source_files is False
    assert config.source_media.upload_file_naming == "original"
    assert config.face.execution_provider_profile == "auto"
    assert config.face.allow_cpu_fallback is True
    assert config.face.execution_providers == ["CPUExecutionProvider"]
    assert config.frame_boxes.write_to_sqlite is True
    assert config.frame_boxes.use_for_video_overlay is True
    assert config.reference_export.frames_per_person == 12
    assert config.reference_export.include_face_box is True
    assert config.large_model.provider == "openai"
    assert isinstance(config.large_model.api_key, str)
    assert config.image_generation.input_fidelity == "high"


def test_config_can_dump_chinese_aliases() -> None:
    """验证配置模型可以按中文别名导出为 JSON。"""
    config = load_config(Path("configs/default.toml"))
    payload = config.model_dump(mode="json", by_alias=True)

    assert payload["视频"]["采样帧率"] == 2.0
    assert payload["人脸"]["模型名称"] == "buffalo_l"
    assert payload["人脸"]["执行提供方策略"] == "auto"
    assert payload["人脸"]["允许CPU降级"] is True
    assert payload["人脸"]["ONNX执行提供方"] == ["CPUExecutionProvider"]
    assert payload["聚类"]["预设人物数量"] is None
    assert payload["输出"]["根目录"] == "_outputs"
    assert payload["源媒体"]["拷贝源文件"] is False
    assert payload["源媒体"]["上传保存命名"] == "original"
    assert payload["逐帧框"]["播放红框使用逐帧框"] is True
    assert payload["参考图导出"]["抽帧策略"] == "best"
    assert isinstance(payload["大模型"]["API Key"], str)
    assert payload["大模型"]["LiteLLM详细调试"] is False
    assert payload["图像生成"]["输出格式"] == "webp"
    assert payload["图像生成"]["输出压缩"] == 85
    assert payload["图像生成"]["请求日志"] is True


def test_analysis_cache_payload_excludes_external_ai_settings() -> None:
    """验证外部大模型配置不会导致视频分析缓存失效。"""
    config = AppConfig()
    config.large_model.api_key = "sk-test"
    config.large_model.model = "gpt-image-test"
    config.image_generation.enabled = True

    payload = config.analysis_cache_payload()

    assert "大模型" not in payload
    assert "图像生成" not in payload
    assert payload["视频"]["采样帧率"] == 2.0


def test_config_include_files_can_be_overridden(tmp_path: Path) -> None:
    """验证 default.toml 可以通过包含配置拆分，并允许入口文件覆盖子配置。"""
    child = tmp_path / "recognition.toml"
    child.write_text(
        """
["视频"]
"采样帧率" = 5.0
""",
        encoding="utf-8",
    )
    entry = tmp_path / "default.toml"
    entry.write_text(
        """
"包含配置" = ["recognition.toml"]

["视频"]
"最小人脸尺寸" = 24
""",
        encoding="utf-8",
    )

    config = load_config(entry)

    assert config.video.sample_fps == 5.0
    assert config.video.min_face_size == 24


def test_anime_profile_configs_load() -> None:
    """验证单视频调参 profile 可以正确包含默认配置并覆盖识别参数。"""
    strict = load_config(Path("configs/profiles/anime-lowres-strict.toml"))
    recall = load_config(Path("configs/profiles/anime-high-recall.toml"))

    assert strict.video.sample_fps == 5.0
    assert strict.video.min_face_size == 40
    assert strict.face.det_score_threshold == 0.62
    assert strict.output.root == Path("_outputs")

    assert recall.video.sample_fps == 5.0
    assert recall.video.min_face_size == 24
    assert recall.face.det_size == (960, 960)
    assert recall.output.root == Path("_outputs")

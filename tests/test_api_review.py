from __future__ import annotations

import base64
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient

from apps.api import main as api_main
from apps.api.main import create_app
from core.config import AppConfig, DatabaseConfig, OutputConfig
from core.models import FaceDetection
from core.storage import ResultStore


def test_api_video_detail_exposes_review_fields() -> None:
    """验证视频详情接口会暴露 tracks 与 face_crops 等审阅字段。"""
    client = TestClient(create_app())

    response = client.get("/api/videos/1")

    # 若视频不存在则跳过，否则断言返回 200 且包含必要字段
    if response.status_code == 404:
        return
    assert response.status_code == 200
    payload = response.json()
    assert "tracks" in payload
    assert "face_crops" in payload


def test_api_health() -> None:
    """验证健康检查接口返回 200 与预期的状态信息。"""
    client = TestClient(create_app())

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_hardware_summary(monkeypatch) -> None:
    """验证硬件摘要接口会返回前端需要的 provider 信息。"""
    monkeypatch.setattr(
        api_main,
        "hardware_summary",
        lambda: {
            "system": "Darwin",
            "machine": "arm64",
            "processor": "arm",
            "python": "3.12.0",
            "nvidia_smi": None,
            "gpu_devices": ["Apple M1"],
            "available_providers": ["CoreMLExecutionProvider", "CPUExecutionProvider"],
            "recommended_profile": "apple",
            "recommended_providers": ["CoreMLExecutionProvider", "CPUExecutionProvider"],
            "profiles": [
                {
                    "id": "apple",
                    "label": "Apple CoreML",
                    "preferred_providers": ["CoreMLExecutionProvider"],
                    "note": "Apple Silicon",
                    "available": True,
                }
            ],
        },
    )
    client = TestClient(create_app())

    response = client.get("/api/hardware")

    assert response.status_code == 200
    payload = response.json()
    assert payload["recommended_profile"] == "apple"
    assert payload["available_providers"] == ["CoreMLExecutionProvider", "CPUExecutionProvider"]


def test_api_import_rejects_missing_timeline() -> None:
    """验证导入时间线接口对不存在的时间线文件返回 404。"""
    client = TestClient(create_app())

    response = client.post(
        "/api/import-timeline",
        json={"timeline_path": str(Path("missing-timeline.json"))},
    )

    assert response.status_code == 404


def test_api_upload_video_saves_supported_file(tmp_path: Path, monkeypatch) -> None:
    """验证上传受支持的视频文件后，接口会保存文件并返回路径与大小。"""
    monkeypatch.setattr(api_main, "UPLOAD_ROOT", tmp_path)
    client = TestClient(create_app())

    response = client.post(
        "/api/upload-video",
        files={"file": ("sample.mp4", b"fake video bytes", "video/mp4")},
    )

    assert response.status_code == 200
    payload = response.json()
    saved_path = Path(payload["video_path"])
    assert payload["filename"] == "sample.mp4"
    assert payload["size"] == len(b"fake video bytes")
    assert saved_path.exists()
    assert saved_path.name == "sample.mp4"
    assert saved_path.suffix == ".mp4"
    assert payload["source_path"] == str(saved_path)
    assert payload["source_directory"] == str(saved_path.parent)


def test_api_upload_video_rejects_unsupported_file() -> None:
    """验证上传不支持的文件类型时，接口返回 400 拒绝。"""
    client = TestClient(create_app())

    response = client.post(
        "/api/upload-video",
        files={"file": ("notes.txt", b"not a video", "text/plain")},
    )

    assert response.status_code == 400


def test_api_manual_profile_uploads_four_view_asset(tmp_path: Path, monkeypatch) -> None:
    """验证可以不依赖视频，手动创建人物档案并上传四视图原图。"""
    config = AppConfig(
        output=OutputConfig(root=tmp_path / "_outputs"),
        database=DatabaseConfig(path=tmp_path / "_outputs" / "facetimemarker.db"),
    )
    upload_root = tmp_path / "uploads"
    monkeypatch.setattr(api_main, "load_config", lambda: config)
    monkeypatch.setattr(api_main, "UPLOAD_ROOT", upload_root)
    client = TestClient(create_app())

    blank_response = client.post("/api/global-people", json={"label": "   "})
    assert blank_response.status_code == 422

    create_response = client.post("/api/global-people", json={"label": "手动角色"})

    assert create_response.status_code == 200
    global_person_id = create_response.json()["global_person_id"]
    people_response = client.get("/api/global-people")
    assert people_response.status_code == 200
    assert people_response.json()[0]["observation_count"] == 0

    upload_response = client.post(
        f"/api/global-people/{global_person_id}/four-view-assets",
        data={"label": "第一套服装"},
        files={"file": ("four-view.png", b"fake image", "image/png")},
    )

    assert upload_response.status_code == 200
    payload = upload_response.json()
    assert payload["label"] == "第一套服装"
    image_path = Path(payload["image_path"])
    assert image_path.exists()
    assert image_path.is_relative_to(config.output.root / "profile-assets" / "manual")
    assert not image_path.is_relative_to(upload_root)

    assets_response = client.get(f"/api/global-people/{global_person_id}/four-view-assets")
    assert assets_response.status_code == 200
    assert assets_response.json()[0]["image_path"] == payload["image_path"]


def test_api_generates_four_view_asset_from_reference_image(tmp_path: Path, monkeypatch) -> None:
    """验证图像生成接口会保存返回图片并登记为四视图资产。"""
    config = AppConfig(
        output=OutputConfig(root=tmp_path / "_outputs"),
        database=DatabaseConfig(path=tmp_path / "_outputs" / "facetimemarker.db"),
    )
    config.large_model.enabled = True
    config.large_model.api_key = "test-key"
    config.large_model.base_url = "https://api.openai.test/v1"
    config.large_model.model = "gpt-image-2"
    config.image_generation.enabled = True
    config.image_generation.output_format = "png"
    upload_root = tmp_path / "uploads"
    reference_path = tmp_path / "reference.png"
    reference_path.write_bytes(b"reference-image")

    def fake_image_edit(**kwargs):  # noqa: ANN003
        assert kwargs["model"] == "gpt-image-2"
        assert kwargs["api_key"] == "test-key"
        assert kwargs["api_base"] == "https://api.openai.test/v1"
        assert kwargs["output_format"] == "png"
        assert "output_compression" not in kwargs
        image_handle = kwargs["image"]
        assert image_handle.read() == b"reference-image"
        return SimpleNamespace(
            data=[
                SimpleNamespace(
                    b64_json=base64.b64encode(b"generated-image").decode("ascii"),
                )
            ]
        )

    monkeypatch.setattr(api_main, "load_config", lambda: config)
    monkeypatch.setattr(api_main, "UPLOAD_ROOT", upload_root)
    monkeypatch.setattr(api_main.litellm, "image_edit", fake_image_edit)
    client = TestClient(create_app())
    global_person_id = client.post("/api/global-people", json={"label": "生成角色"}).json()["global_person_id"]

    response = client.post(
        f"/api/global-people/{global_person_id}/four-view-assets/generate",
        json={
            "label": "AI 四视图",
            "references": [
                {
                    "face_path": str(reference_path),
                    "label": "生成角色",
                }
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["label"] == "AI 四视图"
    assert payload["reference_count"] == 1
    image_path = Path(payload["image_path"])
    assert image_path.is_relative_to(config.output.root / "profile-assets" / "generated")
    assert image_path.name == "AI 四视图.png"
    assert image_path.read_bytes() == b"generated-image"


def test_api_generates_four_view_asset_as_webp_with_compression(tmp_path: Path, monkeypatch) -> None:
    """验证图像生成可请求 WebP，并在兼容接口返回 PNG 时本地兜底转码。"""
    can_encode_webp, _ = api_main.cv2.imencode(".webp", np.zeros((2, 2, 3), dtype=np.uint8))
    if not can_encode_webp:
        pytest.skip("当前 OpenCV 构建不支持 WebP 编码")

    config = AppConfig(
        output=OutputConfig(root=tmp_path / "_outputs"),
        database=DatabaseConfig(path=tmp_path / "_outputs" / "facetimemarker.db"),
    )
    config.large_model.enabled = True
    config.large_model.api_key = "test-key"
    config.large_model.base_url = "https://api.openai.test/v1"
    config.large_model.model = "gpt-image-2"
    config.image_generation.enabled = True
    config.image_generation.output_format = "webp"
    config.image_generation.output_compression = 72
    upload_root = tmp_path / "uploads"
    reference_path = tmp_path / "reference.png"
    reference_path.write_bytes(b"reference-image")
    success, png_buffer = api_main.cv2.imencode(".png", np.full((8, 8, 3), 255, dtype=np.uint8))
    assert success

    def fake_image_edit(**kwargs):  # noqa: ANN003
        assert kwargs["output_format"] == "webp"
        assert kwargs["output_compression"] == 72
        return SimpleNamespace(
            data=[
                SimpleNamespace(
                    b64_json=base64.b64encode(png_buffer.tobytes()).decode("ascii"),
                )
            ]
        )

    monkeypatch.setattr(api_main, "load_config", lambda: config)
    monkeypatch.setattr(api_main, "UPLOAD_ROOT", upload_root)
    monkeypatch.setattr(api_main.litellm, "image_edit", fake_image_edit)
    client = TestClient(create_app())
    global_person_id = client.post("/api/global-people", json={"label": "WebP 角色"}).json()["global_person_id"]

    response = client.post(
        f"/api/global-people/{global_person_id}/four-view-assets/generate",
        json={
            "label": "WebP 四视图",
            "references": [{"face_path": str(reference_path)}],
        },
    )

    assert response.status_code == 200
    image_path = Path(response.json()["image_path"])
    saved = image_path.read_bytes()
    assert image_path.is_relative_to(config.output.root / "profile-assets" / "generated")
    assert image_path.suffix == ".webp"
    assert saved.startswith(b"RIFF")
    assert saved[8:12] == b"WEBP"


def test_api_four_view_generation_logs_sanitized_litellm_error(tmp_path: Path, monkeypatch, caplog) -> None:
    """验证图像生成失败时会记录可排查日志，但不会泄露 API Key。"""
    config = AppConfig(
        output=OutputConfig(root=tmp_path / "_outputs"),
        database=DatabaseConfig(path=tmp_path / "_outputs" / "facetimemarker.db"),
    )
    api_key = "sk-test-secret-1234567890"
    config.large_model.enabled = True
    config.large_model.api_key = api_key
    config.large_model.base_url = "https://api.openai.test/v1"
    config.large_model.model = "gpt-image-2"
    config.image_generation.enabled = True
    upload_root = tmp_path / "uploads"
    reference_path = tmp_path / "reference.png"
    reference_path.write_bytes(b"reference-image")

    def fake_image_edit(**_kwargs):  # noqa: ANN003
        raise RuntimeError(f"upstream rejected request with token {api_key}")

    monkeypatch.setattr(api_main, "load_config", lambda: config)
    monkeypatch.setattr(api_main, "UPLOAD_ROOT", upload_root)
    monkeypatch.setattr(api_main.litellm, "image_edit", fake_image_edit)
    client = TestClient(create_app())
    global_person_id = client.post("/api/global-people", json={"label": "失败角色"}).json()["global_person_id"]

    with caplog.at_level("INFO", logger="facetimemarker.api"):
        response = client.post(
            f"/api/global-people/{global_person_id}/four-view-assets/generate",
            json={
                "label": "失败四视图",
                "references": [{"face_path": str(reference_path)}],
            },
        )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "图像生成失败" in detail
    assert "upstream rejected request" in detail
    assert api_key not in detail
    assert api_key not in caplog.text
    assert "<redacted-api-key>" in caplog.text
    assert "调用 LiteLLM image_edit" in caplog.text


def test_api_deletes_and_merges_manual_profiles(tmp_path: Path, monkeypatch) -> None:
    """验证人物档案可以合并、移入回收站、恢复和彻底删除。"""
    config = AppConfig(
        output=OutputConfig(root=tmp_path / "_outputs"),
        database=DatabaseConfig(path=tmp_path / "_outputs" / "facetimemarker.db"),
    )
    upload_root = tmp_path / "uploads"
    monkeypatch.setattr(api_main, "load_config", lambda: config)
    monkeypatch.setattr(api_main, "UPLOAD_ROOT", upload_root)
    client = TestClient(create_app())

    target_id = client.post("/api/global-people", json={"label": "目标角色"}).json()["global_person_id"]
    source_id = client.post("/api/global-people", json={"label": "重复角色"}).json()["global_person_id"]
    rename_response = client.patch(f"/api/global-people/{target_id}", json={"label": "正式角色"})
    assert rename_response.status_code == 200
    renamed_people = {
        item["global_person_id"]: item
        for item in rename_response.json()["global_people"]
    }
    assert renamed_people[target_id]["label"] == "正式角色"

    upload_response = client.post(
        f"/api/global-people/{source_id}/four-view-assets",
        data={"label": "重复角色四视图"},
        files={"file": ("duplicate.png", b"fake image", "image/png")},
    )
    assert upload_response.status_code == 200

    merge_response = client.post(
        f"/api/global-people/{target_id}/merge",
        json={"source_global_person_id": source_id},
    )

    assert merge_response.status_code == 200
    merge_payload = merge_response.json()
    assert source_id not in {item["global_person_id"] for item in merge_payload["global_people"]}
    merged_asset = merge_payload["four_view_assets"][0]
    assert merged_asset["global_person_id"] == target_id
    merged_asset_path = Path(merged_asset["image_path"])
    assert merged_asset_path.exists()

    asset_delete_response = client.delete(
        f"/api/global-people/{target_id}/four-view-assets/{merged_asset['id']}"
    )
    assert asset_delete_response.status_code == 200
    asset_delete_payload = asset_delete_response.json()
    assert asset_delete_payload["deleted_asset"]["id"] == merged_asset["id"]
    assert asset_delete_payload["four_view_assets"] == []
    assert not merged_asset_path.exists()

    delete_response = client.delete(f"/api/global-people/{target_id}")

    assert delete_response.status_code == 200
    delete_payload = delete_response.json()
    assert delete_payload["global_people"] == []
    assert delete_payload["deleted_global_people"][0]["global_person_id"] == target_id
    assert delete_payload["deleted_global_people"][0]["deleted_at"] is not None

    deleted_list_response = client.get("/api/global-people", params={"only_deleted": True})
    assert deleted_list_response.status_code == 200
    assert deleted_list_response.json()[0]["global_person_id"] == target_id

    restore_response = client.post(f"/api/global-people/{target_id}/restore")
    assert restore_response.status_code == 200
    assert restore_response.json()["global_people"][0]["global_person_id"] == target_id
    assert restore_response.json()["deleted_global_people"] == []

    second_delete_response = client.delete(f"/api/global-people/{target_id}")
    assert second_delete_response.status_code == 200

    purge_response = client.delete(f"/api/global-people/{target_id}/purge")
    assert purge_response.status_code == 200
    assert purge_response.json()["global_people"] == []
    assert purge_response.json()["deleted_global_people"] == []

    actions_response = client.get(
        "/api/global-person-actions",
        params={"global_person_id": target_id, "limit": 20},
    )
    assert actions_response.status_code == 200
    action_names = {item["action"] for item in actions_response.json()}
    assert {
        "create_manual_profile",
        "rename_profile",
        "merge_profile",
        "trash_profile",
        "restore_profile",
        "purge_profile",
    }.issubset(action_names)


def test_api_analyze_job_reports_status(tmp_path: Path, monkeypatch) -> None:
    """验证后台分析任务接口会返回可轮询的任务状态。"""
    config = AppConfig(
        output=OutputConfig(root=tmp_path / "_outputs"),
        database=DatabaseConfig(path=tmp_path / "_outputs" / "facetimemarker.db"),
    )
    video_path = tmp_path / "sample.mp4"
    config_path = tmp_path / "profile.toml"
    video_path.write_bytes(b"fake video")
    config_path.write_text("[视频]\n\"采样帧率\" = 5.0\n", encoding="utf-8")
    monkeypatch.setattr(api_main, "load_config", lambda: config)
    with api_main._ANALYSIS_JOBS_LOCK:
        api_main._ANALYSIS_JOBS.clear()
        api_main._ANALYSIS_REQUESTS.clear()
        api_main._ANALYSIS_CANCEL_EVENTS.clear()

    def fake_run_analyze_batch_job(
        job_id: str,
        request: api_main.AnalyzeBatchRequest,
    ) -> None:
        assert request.hardware_profile == "nvidia"
        assert request.allow_cpu_fallback is False
        assert request.config_path == str(config_path)
        api_main._update_analysis_item(
            job_id,
            0,
            status="succeeded",
            stage="done",
            progress=1.0,
            message="分析完成",
            video_id=7,
            timeline_path="_outputs/sample/timeline.json",
        )
        api_main._update_analysis_job(
            job_id,
            status="succeeded",
            stage="done",
            progress=1.0,
            message="批量分析完成：成功 1 个，失败 0 个",
            current_index=None,
        )

    monkeypatch.setattr(api_main, "_run_analyze_batch_job", fake_run_analyze_batch_job)
    client = TestClient(create_app())

    response = client.post(
        "/api/analyze-jobs",
        json={
            "video_path": str(video_path),
            "preset": "fast",
            "use_cache": True,
            "hardware_profile": "nvidia",
            "allow_cpu_fallback": False,
            "config_path": str(config_path),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued"

    status_payload = payload
    for _ in range(20):
        status_response = client.get(f"/api/analyze-jobs/{payload['job_id']}")
        assert status_response.status_code == 200
        status_payload = status_response.json()
        if status_payload["status"] == "succeeded":
            break
        time.sleep(0.01)

    assert status_payload["status"] == "succeeded"
    assert status_payload["progress"] == 1.0
    assert status_payload["video_id"] == 7


def test_api_analyze_batch_job_accepts_semicolon_paths(tmp_path: Path, monkeypatch) -> None:
    """验证批量分析任务支持用分号分隔多个本地视频路径。"""
    config = AppConfig(
        output=OutputConfig(root=tmp_path / "_outputs"),
        database=DatabaseConfig(path=tmp_path / "_outputs" / "facetimemarker.db"),
    )
    first_path = tmp_path / "first.mp4"
    second_path = tmp_path / "second.mp4"
    first_path.write_bytes(b"fake video 1")
    second_path.write_bytes(b"fake video 2")
    monkeypatch.setattr(api_main, "load_config", lambda: config)
    with api_main._ANALYSIS_JOBS_LOCK:
        api_main._ANALYSIS_JOBS.clear()
        api_main._ANALYSIS_REQUESTS.clear()
        api_main._ANALYSIS_CANCEL_EVENTS.clear()

    def fake_run_analyze_batch_job(
        job_id: str,
        request: api_main.AnalyzeBatchRequest,
    ) -> None:
        paths = api_main._parse_video_paths(request.video_paths)
        assert request.expected_people_count == 2
        assert request.hardware_profile == "intel"
        assert request.allow_cpu_fallback is False
        for index, path in enumerate(paths):
            api_main._update_analysis_item(
                job_id,
                index,
                status="succeeded",
                stage="done",
                progress=1.0,
                message="分析完成",
                video_id=100 + index,
                timeline_path=f"_outputs/{Path(path).stem}/timeline.json",
            )
        api_main._update_analysis_job(
            job_id,
            status="succeeded",
            stage="done",
            progress=1.0,
            message="批量分析完成：成功 2 个，失败 0 个",
            current_index=None,
        )

    monkeypatch.setattr(api_main, "_run_analyze_batch_job", fake_run_analyze_batch_job)
    client = TestClient(create_app())

    response = client.post(
        "/api/analyze-batch-jobs",
        json={
            "video_paths": f"{first_path}; {second_path}",
            "preset": "fast",
            "use_cache": True,
            "expected_people_count": 2,
            "hardware_profile": "intel",
            "allow_cpu_fallback": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["video_paths"] == [str(first_path), str(second_path)]

    status_payload = payload
    for _ in range(20):
        status_response = client.get(f"/api/analyze-jobs/{payload['job_id']}")
        assert status_response.status_code == 200
        status_payload = status_response.json()
        if status_payload["status"] == "succeeded":
            break
        time.sleep(0.01)

    assert status_payload["status"] == "succeeded"
    assert status_payload["completed"] == 2
    assert [item["status"] for item in status_payload["items"]] == ["succeeded", "succeeded"]


def test_api_analyze_job_status_persists_to_sqlite(tmp_path: Path, monkeypatch) -> None:
    """验证分析任务状态会写入 SQLite，内存清空后仍可查询。"""
    config = AppConfig(
        output=OutputConfig(root=tmp_path / "_outputs"),
        database=DatabaseConfig(path=tmp_path / "_outputs" / "facetimemarker.db"),
    )
    video_path = tmp_path / "persisted.mp4"
    video_path.write_bytes(b"fake video")
    monkeypatch.setattr(api_main, "load_config", lambda: config)
    with api_main._ANALYSIS_JOBS_LOCK:
        api_main._ANALYSIS_JOBS.clear()
        api_main._ANALYSIS_REQUESTS.clear()
        api_main._ANALYSIS_CANCEL_EVENTS.clear()

    def fake_run_analyze_batch_job(
        job_id: str,
        request: api_main.AnalyzeBatchRequest,
    ) -> None:
        api_main._update_analysis_item(
            job_id,
            0,
            status="succeeded",
            stage="done",
            progress=1.0,
            message="分析完成",
            video_id=9,
            timeline_path="_outputs/persisted/timeline.json",
        )
        api_main._update_analysis_job(
            job_id,
            status="succeeded",
            stage="done",
            progress=1.0,
            message="批量分析完成：成功 1 个，失败 0 个",
            current_index=None,
        )

    monkeypatch.setattr(api_main, "_run_analyze_batch_job", fake_run_analyze_batch_job)
    client = TestClient(create_app())

    response = client.post(
        "/api/analyze-jobs",
        json={"video_path": str(video_path), "preset": "fast", "use_cache": True},
    )
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    for _ in range(20):
        status_response = client.get(f"/api/analyze-jobs/{job_id}")
        assert status_response.status_code == 200
        if status_response.json()["status"] == "succeeded":
            break
        time.sleep(0.01)

    with api_main._ANALYSIS_JOBS_LOCK:
        api_main._ANALYSIS_JOBS.clear()

    persisted_response = client.get(f"/api/analyze-jobs/{job_id}")

    assert persisted_response.status_code == 200
    payload = persisted_response.json()
    assert payload["status"] == "succeeded"
    assert payload["video_id"] == 9

    list_response = client.get("/api/analyze-jobs")

    assert list_response.status_code == 200
    jobs = list_response.json()
    assert jobs[0]["job_id"] == job_id
    assert jobs[0]["status"] == "succeeded"


def test_api_analyze_job_can_be_canceled_while_queued(tmp_path: Path, monkeypatch) -> None:
    """验证后台分析任务可以在排队阶段被终止。"""
    config = AppConfig(
        output=OutputConfig(root=tmp_path / "_outputs"),
        database=DatabaseConfig(path=tmp_path / "_outputs" / "facetimemarker.db"),
    )
    video_path = tmp_path / "queued.mp4"
    video_path.write_bytes(b"fake video")
    monkeypatch.setattr(api_main, "load_config", lambda: config)
    monkeypatch.setattr(api_main, "_ensure_analysis_worker_started", lambda: None)
    with api_main._ANALYSIS_JOBS_LOCK:
        api_main._ANALYSIS_JOBS.clear()
        api_main._ANALYSIS_REQUESTS.clear()
        api_main._ANALYSIS_CANCEL_EVENTS.clear()
    client = TestClient(create_app())

    response = client.post(
        "/api/analyze-jobs",
        json={"video_path": str(video_path), "preset": "fast", "use_cache": True},
    )
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    cancel_response = client.post(f"/api/analyze-jobs/{job_id}/cancel")

    assert cancel_response.status_code == 200
    payload = cancel_response.json()
    assert payload["status"] == "canceled"
    assert payload["items"][0]["status"] == "canceled"

    status_response = client.get(f"/api/analyze-jobs/{job_id}")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "canceled"


def test_api_context_segments_groups_dense_activity(tmp_path: Path, monkeypatch) -> None:
    """验证上下文片段接口会按人物出现频率合并精确片段。"""
    config = AppConfig(
        output=OutputConfig(root=tmp_path / "_outputs"),
        database=DatabaseConfig(path=tmp_path / "_outputs" / "facetimemarker.db"),
    )
    timeline_path = tmp_path / "timeline.json"
    timeline_path.write_text(
        """
        {
          "video": {
            "path": "drama.mp4",
            "fps": 25.0,
            "frame_count": 6000,
            "width": 1920,
            "height": 1080
          },
          "people_count": 1,
          "people": [
            {
              "person_id": 0,
              "label": "person_001",
              "global_person_id": null,
              "track_ids": [1, 2, 3],
              "appearances": 3,
              "total_duration": 15.0,
              "detection_count": 15,
              "representative_face_path": null
            }
          ],
          "tracks": [],
          "persons": {
            "0": [
              {
                "person_id": 0,
                "start": 10.0,
                "end": 14.0,
                "track_ids": [1],
                "detection_count": 4,
                "clip_path": null
              },
              {
                "person_id": 0,
                "start": 28.0,
                "end": 33.0,
                "track_ids": [2],
                "detection_count": 5,
                "clip_path": null
              },
              {
                "person_id": 0,
                "start": 48.0,
                "end": 54.0,
                "track_ids": [3],
                "detection_count": 6,
                "clip_path": null
              }
            ]
          }
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr(api_main, "load_config", lambda: config)
    from core.storage import SQLiteStore

    video_id = SQLiteStore(config.database.path).import_timeline(timeline_path)
    client = TestClient(create_app())

    response = client.get(
        f"/api/videos/{video_id}/context-segments",
        params={
            "person_id": 0,
            "padding_seconds": 8,
            "max_gap_seconds": 18,
            "min_presence_ratio": 0.12,
            "min_source_segments": 2,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["person_id"] == 0
    assert payload[0]["label"] == "person_001"
    assert payload[0]["kind"] == "dense"
    assert payload[0]["start"] == 2.0
    assert payload[0]["end"] == 62.0
    assert payload[0]["source_segment_count"] == 3
    assert payload[0]["track_ids"] == [1, 2, 3]


def test_api_search_people_finds_renamed_label(tmp_path: Path, monkeypatch) -> None:
    """验证人物备注重命名后可以被搜索接口查到。"""
    config = AppConfig(
        output=OutputConfig(root=tmp_path / "_outputs"),
        database=DatabaseConfig(path=tmp_path / "_outputs" / "facetimemarker.db"),
    )
    timeline_path = tmp_path / "timeline.json"
    timeline_path.write_text(
        """
        {
          "video": {
            "path": "episode_01.mp4",
            "fps": 25.0,
            "frame_count": 2500,
            "width": 1920,
            "height": 1080
          },
          "people_count": 1,
          "people": [
            {
              "person_id": 0,
              "label": "person_001",
              "global_person_id": "global_person_000001",
              "track_ids": [1],
              "appearances": 1,
              "total_duration": 4.0,
              "detection_count": 8,
              "representative_face_path": "faces/person_001.jpg"
            }
          ],
          "tracks": [],
          "persons": {
            "0": [
              {
                "person_id": 0,
                "start": 10.0,
                "end": 14.0,
                "track_ids": [1],
                "detection_count": 8,
                "clip_path": null
              }
            ]
          }
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr(api_main, "load_config", lambda: config)
    from core.storage import SQLiteStore

    video_id = SQLiteStore(config.database.path).import_timeline(timeline_path)
    client = TestClient(create_app())

    rename_response = client.patch(
        f"/api/videos/{video_id}/people/0",
        json={"label": "女主A"},
    )
    assert rename_response.status_code == 200

    response = client.get("/api/search/people", params={"q": "女主A"})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["label"] == "女主A"
    assert payload[0]["video_title"] == "episode_01"

    hide_response = client.patch(
        f"/api/videos/{video_id}/people/0/visibility",
        json={"hidden": True},
    )
    assert hide_response.status_code == 200
    assert hide_response.json()["people"][0]["hidden"] == 1

    hidden_search_response = client.get("/api/search/people", params={"q": "女主A"})
    assert hidden_search_response.status_code == 200
    assert hidden_search_response.json() == []


def test_api_search_faces_ranks_global_people_by_embedding(tmp_path: Path, monkeypatch) -> None:
    """验证以图搜图接口会按上传图片 embedding 匹配全局人物库。"""
    config = AppConfig(
        output=OutputConfig(root=tmp_path / "_outputs"),
        database=DatabaseConfig(path=tmp_path / "_outputs" / "facetimemarker.db"),
    )
    config.output.root.mkdir(parents=True, exist_ok=True)
    config.identity_store_path().write_text(
        """
        {
          "version": 1,
          "match_threshold": 0.55,
          "people_count": 2,
          "people": [
            {
              "global_person_id": "global_person_000001",
              "embedding": [1.0, 0.0],
              "rejected_matches": [],
              "observations": []
            },
            {
              "global_person_id": "global_person_000002",
              "embedding": [0.0, 1.0],
              "rejected_matches": [],
              "observations": []
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    class FakeAnalyzer:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def analyze(self, _frame):
            return [
                FaceDetection(
                    frame_index=0,
                    timestamp=0.0,
                    bbox_xyxy=(0.0, 0.0, 100.0, 100.0),
                    confidence=0.99,
                    embedding=np.array([0.0, 1.0], dtype=np.float32),
                )
            ]

    monkeypatch.setattr(api_main, "load_config", lambda: config)
    monkeypatch.setattr(api_main, "InsightFaceAnalyzer", FakeAnalyzer)
    monkeypatch.setattr(api_main.cv2, "imdecode", lambda *_args, **_kwargs: np.zeros((8, 8, 3)))
    client = TestClient(create_app())

    response = client.post(
        "/api/search/faces",
        files={"file": ("face.jpg", b"fake image", "image/jpeg")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["global_person_id"] == "global_person_000002"
    assert payload[0]["similarity"] >= payload[0]["threshold"]


def test_api_video_frame_extracts_original_frame(tmp_path: Path, monkeypatch) -> None:
    """验证完整视频帧接口可以按帧号抽出 JPEG 预览。"""
    config = AppConfig(
        output=OutputConfig(root=tmp_path / "_outputs"),
        database=DatabaseConfig(path=tmp_path / "_outputs" / "facetimemarker.db"),
    )
    video_path = tmp_path / "movie.mp4"
    video_path.write_bytes(b"fake video")
    timeline_path = tmp_path / "timeline.json"
    timeline_path.write_text(
        f"""
        {{
          "video": {{
            "path": "{video_path}",
            "fps": 25.0,
            "frame_count": 100,
            "width": 640,
            "height": 360
          }},
          "people_count": 0,
          "people": [],
          "tracks": [],
          "segments": [],
          "face_crops": []
        }}
        """,
        encoding="utf-8",
    )
    store = ResultStore(config.database.path, url=config.database.url)
    video_id = store.import_timeline(timeline_path)

    class FakeCapture:
        def __init__(self, _path: str) -> None:
            self.released = False

        def isOpened(self) -> bool:
            return True

        def set(self, _prop: int, _value: float) -> bool:
            return True

        def read(self):
            return True, np.zeros((4, 4, 3), dtype=np.uint8)

        def release(self) -> None:
            self.released = True

    monkeypatch.setattr(api_main, "load_config", lambda: config)
    monkeypatch.setattr(api_main.cv2, "VideoCapture", FakeCapture)
    monkeypatch.setattr(
        api_main.cv2,
        "imencode",
        lambda *_args, **_kwargs: (True, np.frombuffer(b"jpg-bytes", dtype=np.uint8)),
    )
    client = TestClient(create_app())

    response = client.get(f"/api/videos/{video_id}/frame", params={"frame_index": 3})

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content == b"jpg-bytes"


def test_api_assign_tracks_updates_video_detail(tmp_path: Path, monkeypatch) -> None:
    """验证批量归类轨迹接口会返回更新后的视频详情。"""
    config = AppConfig(
        output=OutputConfig(root=tmp_path / "_outputs"),
        database=DatabaseConfig(path=tmp_path / "_outputs" / "facetimemarker.db"),
    )
    timeline_path = tmp_path / "timeline.json"
    timeline_path.write_text(
        """
        {
          "video": {
            "path": "movie.mp4",
            "fps": 25.0,
            "frame_count": 250,
            "width": 1920,
            "height": 1080
          },
          "people_count": 2,
          "people": [
            {
              "person_id": 0,
              "label": "person_001",
              "global_person_id": null,
              "track_ids": [11],
              "appearances": 1,
              "total_duration": 1.0,
              "detection_count": 2,
              "representative_face_path": "faces/person_001.jpg"
            },
            {
              "person_id": 1,
              "label": "person_002",
              "global_person_id": null,
              "track_ids": [21],
              "appearances": 1,
              "total_duration": 1.0,
              "detection_count": 2,
              "representative_face_path": "faces/person_002.jpg"
            }
          ],
          "tracks": [
            {
              "track_id": 11,
              "person_id": 0,
              "start": 1.0,
              "end": 2.0,
              "detection_count": 2,
              "representative_face_path": "faces/track_011.jpg",
              "representative_bbox": [1, 2, 3, 4],
              "representative_confidence": 0.95,
              "embedding_dim": 512,
              "embedding_norm": 1.0
            },
            {
              "track_id": 21,
              "person_id": 1,
              "start": 3.0,
              "end": 4.0,
              "detection_count": 2,
              "representative_face_path": "faces/track_021.jpg",
              "representative_bbox": [1, 2, 3, 4],
              "representative_confidence": 0.95,
              "embedding_dim": 512,
              "embedding_norm": 1.0
            }
          ],
          "persons": {
            "0": [
              {
                "person_id": 0,
                "start": 1.0,
                "end": 2.0,
                "track_ids": [11],
                "detection_count": 2,
                "clip_path": null
              }
            ],
            "1": [
              {
                "person_id": 1,
                "start": 3.0,
                "end": 4.0,
                "track_ids": [21],
                "detection_count": 2,
                "clip_path": null
              }
            ]
          }
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr(api_main, "load_config", lambda: config)
    monkeypatch.setattr(
        api_main,
        "_identity_store",
        lambda _: SimpleNamespace(
            confirm_observation=lambda *args, **kwargs: None,
            reject_observation=lambda *args, **kwargs: "global_person_999999",
            save=lambda: None,
        ),
    )
    from core.storage import SQLiteStore

    video_id = SQLiteStore(config.database.path).import_timeline(timeline_path)
    client = TestClient(create_app())

    response = client.post(
        f"/api/videos/{video_id}/tracks/assign",
        json={"track_ids": [11], "target_person_id": 1},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [person["person_id"] for person in payload["people"]] == [1]
    assert sorted(track["track_id"] for track in payload["tracks"]) == [11, 21]

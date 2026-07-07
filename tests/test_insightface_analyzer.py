from types import SimpleNamespace

import pytest

from adapters.face import insightface_analyzer
from adapters.face.insightface_analyzer import _available_execution_providers
from core import hardware
from core.hardware import resolve_execution_providers


def test_available_execution_providers_keeps_cpu_fallback(monkeypatch) -> None:
    """验证不可用的 ONNX provider 会被过滤，并保留 CPU 回退。"""
    monkeypatch.setitem(
        __import__("sys").modules,
        "onnxruntime",
        SimpleNamespace(get_available_providers=lambda: ["CPUExecutionProvider"]),
    )

    providers = _available_execution_providers(
        ["CUDAExecutionProvider", "CPUExecutionProvider"],
    )

    assert providers == ["CPUExecutionProvider"]


def test_available_execution_providers_preserves_available_priority(monkeypatch) -> None:
    """验证可用 provider 会按配置顺序保留。"""
    monkeypatch.setitem(
        __import__("sys").modules,
        "onnxruntime",
        SimpleNamespace(
            get_available_providers=lambda: [
                "CPUExecutionProvider",
                "CoreMLExecutionProvider",
            ]
        ),
    )

    providers = insightface_analyzer._available_execution_providers(
        ["CoreMLExecutionProvider", "CPUExecutionProvider"],
    )

    assert providers == ["CoreMLExecutionProvider", "CPUExecutionProvider"]


def test_available_execution_providers_can_disable_cpu_fallback(monkeypatch) -> None:
    """验证关闭 CPU 降级后，不会把 CPU 自动塞回 provider 列表。"""
    monkeypatch.setitem(
        __import__("sys").modules,
        "onnxruntime",
        SimpleNamespace(
            get_available_providers=lambda: [
                "CUDAExecutionProvider",
                "CPUExecutionProvider",
            ]
        ),
    )

    providers = _available_execution_providers(
        ["CUDAExecutionProvider", "CPUExecutionProvider"],
        profile="nvidia",
        allow_cpu_fallback=False,
    )

    assert providers == ["CUDAExecutionProvider"]


def test_unavailable_profile_raises_when_cpu_fallback_disabled(monkeypatch) -> None:
    """验证指定 GPU profile 但不可用且禁用降级时，会直接报错。"""
    monkeypatch.setitem(
        __import__("sys").modules,
        "onnxruntime",
        SimpleNamespace(get_available_providers=lambda: ["CPUExecutionProvider"]),
    )

    with pytest.raises(RuntimeError):
        _available_execution_providers(
            ["CUDAExecutionProvider", "CPUExecutionProvider"],
            profile="nvidia",
            allow_cpu_fallback=False,
        )


def test_auto_profile_prefers_coreml_on_apple_silicon(monkeypatch) -> None:
    """验证 Apple Silicon 环境下 auto 会优先选择 CoreML。"""
    monkeypatch.setattr(hardware.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(hardware.platform, "machine", lambda: "arm64")

    providers = resolve_execution_providers(
        "auto",
        requested_providers=None,
        allow_cpu_fallback=True,
        available_providers=["CoreMLExecutionProvider", "CPUExecutionProvider"],
    )

    assert providers == ["CoreMLExecutionProvider", "CPUExecutionProvider"]


def test_intel_profile_prefers_openvino_then_directml() -> None:
    """验证 Intel profile 优先 OpenVINO，其次 DirectML。"""
    providers = resolve_execution_providers(
        "intel",
        requested_providers=None,
        allow_cpu_fallback=True,
        available_providers=[
            "CPUExecutionProvider",
            "DmlExecutionProvider",
            "OpenVINOExecutionProvider",
        ],
    )

    assert providers == [
        "OpenVINOExecutionProvider",
        "DmlExecutionProvider",
        "CPUExecutionProvider",
    ]

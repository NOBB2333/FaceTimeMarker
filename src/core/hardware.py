from __future__ import annotations

import platform
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any

CPU_PROVIDER = "CPUExecutionProvider"
COREML_PROVIDER = "CoreMLExecutionProvider"
CUDA_PROVIDER = "CUDAExecutionProvider"
OPENVINO_PROVIDER = "OpenVINOExecutionProvider"
DML_PROVIDER = "DmlExecutionProvider"

HARDWARE_PROFILES = ("auto", "cpu", "apple", "nvidia", "intel")


@dataclass(frozen=True)
class HardwareProfile:
    """运行时硬件 provider 策略。"""

    id: str
    label: str
    preferred_providers: tuple[str, ...]
    note: str


PROFILE_DEFINITIONS: dict[str, HardwareProfile] = {
    "auto": HardwareProfile(
        id="auto",
        label="Auto",
        preferred_providers=(),
        note="按当前 ONNX Runtime 可用 provider 和系统自动选择。",
    ),
    "cpu": HardwareProfile(
        id="cpu",
        label="CPU",
        preferred_providers=(CPU_PROVIDER,),
        note="最稳定，速度取决于 CPU。",
    ),
    "apple": HardwareProfile(
        id="apple",
        label="Apple CoreML",
        preferred_providers=(COREML_PROVIDER,),
        note="适合 Apple Silicon；需要 onnxruntime 包含 CoreMLExecutionProvider。",
    ),
    "nvidia": HardwareProfile(
        id="nvidia",
        label="NVIDIA CUDA",
        preferred_providers=(CUDA_PROVIDER,),
        note="适合 NVIDIA GPU；需要 CUDA 版 ONNX Runtime 和匹配驱动。",
    ),
    "intel": HardwareProfile(
        id="intel",
        label="Intel GPU",
        preferred_providers=(OPENVINO_PROVIDER, DML_PROVIDER),
        note="适合 Intel Arc/A770；优先 OpenVINO，Windows 可用 DirectML。",
    ),
}


def get_available_onnx_providers() -> list[str]:
    """返回当前 Python 环境里的 ONNX Runtime provider 列表。"""
    try:
        import onnxruntime as ort
    except ImportError:
        return []
    return list(ort.get_available_providers())


def resolve_execution_providers(
    profile: str,
    requested_providers: list[str] | None,
    allow_cpu_fallback: bool,
    available_providers: list[str] | None = None,
) -> list[str]:
    """按策略解析最终传给 InsightFace/ONNX Runtime 的 provider 顺序。"""
    available = (
        available_providers if available_providers is not None else get_available_onnx_providers()
    )
    available_set = set(available)
    profile_id = _normalize_profile(profile)

    if profile_id == "auto":
        candidates = _auto_provider_order(available, platform.system(), platform.machine())
    elif profile_id == "cpu":
        candidates = [CPU_PROVIDER]
    elif profile_id in PROFILE_DEFINITIONS:
        candidates = list(PROFILE_DEFINITIONS[profile_id].preferred_providers)
    else:
        candidates = list(requested_providers or [])

    providers = [provider for provider in candidates if provider in available_set]
    if allow_cpu_fallback and CPU_PROVIDER in available_set and CPU_PROVIDER not in providers:
        providers.append(CPU_PROVIDER)
    if (
        not providers
        and CPU_PROVIDER in available_set
        and (allow_cpu_fallback or profile_id == "cpu")
    ):
        providers = [CPU_PROVIDER]
    if not providers:
        raise RuntimeError(
            "No requested ONNX Runtime execution provider is available. "
            f"profile={profile_id}, requested={candidates}, available={available}"
        )
    return providers


def hardware_summary() -> dict[str, Any]:
    """生成前端展示和排查用的硬件/Provider 摘要。"""
    available = get_available_onnx_providers()
    system = platform.system()
    machine = platform.machine()
    recommended_profile = recommend_profile(available, system, machine)
    try:
        recommended_providers = resolve_execution_providers(
            recommended_profile,
            requested_providers=None,
            allow_cpu_fallback=True,
            available_providers=available,
        )
    except RuntimeError:
        recommended_providers = []
    return {
        "system": system,
        "machine": machine,
        "processor": platform.processor(),
        "python": platform.python_version(),
        "nvidia_smi": _nvidia_smi_summary(),
        "gpu_devices": _gpu_device_summary(system),
        "available_providers": available,
        "recommended_profile": recommended_profile,
        "recommended_providers": recommended_providers,
        "profiles": [
            {
                "id": item.id,
                "label": item.label,
                "preferred_providers": list(item.preferred_providers),
                "note": item.note,
                "available": any(provider in available for provider in item.preferred_providers)
                if item.id not in {"auto", "cpu"}
                else item.id == "auto" or CPU_PROVIDER in available,
            }
            for item in PROFILE_DEFINITIONS.values()
        ],
    }


def recommend_profile(
    available_providers: list[str] | None = None,
    system: str | None = None,
    machine: str | None = None,
) -> str:
    """根据系统和可用 provider 推荐硬件策略。"""
    available = (
        available_providers if available_providers is not None else get_available_onnx_providers()
    )
    available_set = set(available)
    current_system = system or platform.system()
    current_machine = (machine or platform.machine()).lower()
    if (
        current_system == "Darwin"
        and current_machine in {"arm64", "aarch64"}
        and COREML_PROVIDER in available_set
    ):
        return "apple"
    if CUDA_PROVIDER in available_set:
        return "nvidia"
    if OPENVINO_PROVIDER in available_set or DML_PROVIDER in available_set:
        return "intel"
    return "cpu"


def _auto_provider_order(available: list[str], system: str, machine: str) -> list[str]:
    profile = recommend_profile(available, system, machine)
    if profile == "cpu":
        return [CPU_PROVIDER]
    return list(PROFILE_DEFINITIONS[profile].preferred_providers)


def _normalize_profile(profile: str | None) -> str:
    value = (profile or "auto").strip().lower()
    aliases = {
        "apple_coreml": "apple",
        "coreml": "apple",
        "cuda": "nvidia",
        "nvidia_cuda": "nvidia",
        "arc": "intel",
        "a770": "intel",
        "openvino": "intel",
        "directml": "intel",
    }
    return aliases.get(value, value)


def _nvidia_smi_summary() -> str | None:
    if shutil.which("nvidia-smi") is None:
        return None
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"],
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    output = result.stdout.strip()
    return output or None


def _gpu_device_summary(system: str) -> list[str]:
    """尽力读取显卡名称；真正是否可加速仍以 ONNX Runtime provider 为准。"""
    if system == "Darwin":
        return _command_lines(
            ["system_profiler", "SPDisplaysDataType"],
            prefixes=("Chipset Model:",),
            strip_prefix=True,
        )
    if system == "Windows":
        return _command_lines(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name",
            ],
        )
    if system == "Linux":
        return _command_lines(
            ["sh", "-c", "lspci | grep -Ei 'vga|3d|display'"],
        )
    return []


def _command_lines(
    command: list[str],
    prefixes: tuple[str, ...] = (),
    strip_prefix: bool = False,
) -> list[str]:
    if shutil.which(command[0]) is None:
        return []
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    lines: list[str] = []
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if prefixes and not any(line.startswith(prefix) for prefix in prefixes):
            continue
        if strip_prefix:
            for prefix in prefixes:
                if line.startswith(prefix):
                    line = line.removeprefix(prefix).strip()
                    break
        if line and line not in lines:
            lines.append(line)
    return lines

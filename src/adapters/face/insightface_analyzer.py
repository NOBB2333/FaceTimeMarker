from __future__ import annotations

from core.config import FaceConfig
from core.hardware import CPU_PROVIDER, resolve_execution_providers
from core.models import FaceDetection, Frame


class InsightFaceAnalyzer:
    """基于 InsightFace 的人脸检测与特征提取器。"""

    def __init__(self, config: FaceConfig) -> None:
        """初始化分析器，模型实例按需懒加载。"""
        self.config = config
        self._app = None

    def load(self) -> None:
        """加载 InsightFace 模型并准备推理环境。"""
        try:
            from insightface.app import FaceAnalysis
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("未安装 InsightFace，请运行：uv sync --extra vision") from exc

        providers = _available_execution_providers(
            self.config.execution_providers,
            profile=self.config.execution_provider_profile,
            allow_cpu_fallback=self.config.allow_cpu_fallback,
        )
        try:
            self._app = _create_face_analysis(
                FaceAnalysis,
                self.config.model_name,
                providers,
                self.config.det_size,
            )
        except Exception:
            if (
                not self.config.allow_cpu_fallback
                or providers == [CPU_PROVIDER]
                or CPU_PROVIDER not in providers
            ):
                raise
            self._app = _create_face_analysis(
                FaceAnalysis,
                self.config.model_name,
                [CPU_PROVIDER],
                self.config.det_size,
            )

    def analyze(self, frame: Frame) -> list[FaceDetection]:
        """检测单帧中的人脸并返回置信度达标的人脸信息。"""
        if self._app is None:
            self.load()

        faces = self._app.get(frame.image)
        detections: list[FaceDetection] = []
        for face in faces:
            confidence = float(face.det_score)
            # 过滤掉置信度低于阈值的检测结果
            if confidence < self.config.det_score_threshold:
                continue
            x1, y1, x2, y2 = (float(value) for value in face.bbox)
            detections.append(
                FaceDetection(
                    frame_index=frame.index,
                    timestamp=frame.timestamp,
                    bbox_xyxy=(x1, y1, x2, y2),
                    confidence=confidence,
                    embedding=face.embedding,
                    landmarks=getattr(face, "kps", None),
                )
            )
        return detections


def _available_execution_providers(
    requested: list[str],
    profile: str = "custom",
    allow_cpu_fallback: bool = True,
) -> list[str]:
    """返回当前环境可用的 ONNX Runtime provider。"""
    try:
        import onnxruntime as ort
    except ImportError as exc:  # pragma: no cover
        if not allow_cpu_fallback:
            raise RuntimeError("未安装 ONNX Runtime，且当前已关闭 CPU 降级。") from exc
        return [CPU_PROVIDER]

    return resolve_execution_providers(
        profile,
        requested,
        allow_cpu_fallback=allow_cpu_fallback,
        available_providers=list(ort.get_available_providers()),
    )


def _create_face_analysis(face_analysis_cls, model_name: str, providers: list[str], det_size):
    ctx_id = 0 if providers[0] != CPU_PROVIDER else -1
    app = face_analysis_cls(name=model_name, providers=providers)
    app.prepare(ctx_id=ctx_id, det_size=det_size)
    return app

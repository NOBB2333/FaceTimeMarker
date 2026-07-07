import numpy as np

from adapters.tracking.boxmot_botsort import _embeddings_or_none
from core.models import FaceDetection


def test_embeddings_or_none_stacks_available_embeddings() -> None:
    """验证 _embeddings_or_none 能将所有人脸嵌入堆叠为二维数组。"""
    detections = [
        FaceDetection(0, 0.0, (0, 0, 10, 10), 0.9, embedding=np.array([1.0, 0.0])),
        FaceDetection(0, 0.0, (20, 20, 30, 30), 0.8, embedding=np.array([0.0, 1.0])),
    ]

    embeddings = _embeddings_or_none(detections)

    assert embeddings is not None
    assert embeddings.shape == (2, 2)


def test_embeddings_or_none_returns_none_when_missing_embedding() -> None:
    """验证只要存在任一缺失嵌入的检测，函数就返回 None。"""
    detections = [
        FaceDetection(0, 0.0, (0, 0, 10, 10), 0.9, embedding=np.array([1.0, 0.0])),
        FaceDetection(0, 0.0, (20, 20, 30, 30), 0.8),
    ]

    assert _embeddings_or_none(detections) is None


def test_embeddings_or_none_returns_empty_array_for_empty_detections() -> None:
    """验证输入为空列表时返回形状为 (0, 0) 的空数组。"""
    embeddings = _embeddings_or_none([])

    assert embeddings is not None
    assert embeddings.shape == (0, 0)

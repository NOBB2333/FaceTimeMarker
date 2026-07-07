from __future__ import annotations

import numpy as np
from sklearn.cluster import HDBSCAN
from sklearn.preprocessing import normalize

from core.clustering.fixed_count import assign_fixed_person_count
from core.config import ClusteringConfig
from core.models import FaceTrack


class HdbscanFaceClusterer:
    """基于 HDBSCAN 的人脸轨迹聚类器。"""

    def __init__(self, config: ClusteringConfig) -> None:
        """初始化 HDBSCAN 聚类配置。"""
        self.config = config

    def assign_person_ids(self, tracks: list[FaceTrack]) -> list[FaceTrack]:
        """对有效轨迹按 embedding 做 HDBSCAN 聚类，噪声点单独编号。"""
        if self.config.expected_people_count is not None and assign_fixed_person_count(
            tracks,
            self.config.expected_people_count,
        ):
            return tracks

        valid_tracks = [track for track in tracks if track.embedding is not None]
        if not valid_tracks:
            return tracks

        # 样本数不足时直接为每条轨迹分配独立人物 ID
        if len(valid_tracks) < self.config.min_cluster_size:
            for index, track in enumerate(valid_tracks):
                track.person_id = index
            return tracks

        embeddings = normalize(np.vstack([track.embedding for track in valid_tracks]))
        labels = HDBSCAN(
            min_cluster_size=min(self.config.min_cluster_size, len(valid_tracks)),
            min_samples=min(self.config.min_samples, len(valid_tracks)),
            cluster_selection_epsilon=self.config.cluster_selection_epsilon,
            metric="euclidean",
            copy=True,
        ).fit_predict(embeddings)

        # HDBSCAN 中 label < 0 表示噪声，为噪声轨迹分配独立编号
        next_noise_id = 1 + max((int(label) for label in labels if label >= 0), default=-1)
        for track, label in zip(valid_tracks, labels, strict=True):
            if label < 0:
                track.person_id = next_noise_id
                next_noise_id += 1
            else:
                track.person_id = int(label)

        return tracks

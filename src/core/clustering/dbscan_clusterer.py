from __future__ import annotations

import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import normalize

from core.clustering.fixed_count import assign_fixed_person_count
from core.config import ClusteringConfig
from core.models import FaceTrack


class DbscanFaceClusterer:
    """基于 DBSCAN 的人脸轨迹聚类器。"""

    def __init__(self, config: ClusteringConfig) -> None:
        """初始化 DBSCAN 聚类配置。"""
        self.config = config

    def assign_person_ids(self, tracks: list[FaceTrack]) -> list[FaceTrack]:
        """对有效轨迹按 embedding 做 DBSCAN 聚类，噪声点单独编号。"""
        if self.config.expected_people_count is not None and assign_fixed_person_count(
            tracks,
            self.config.expected_people_count,
        ):
            return tracks

        valid_tracks = [track for track in tracks if track.embedding is not None]
        if not valid_tracks:
            return tracks

        # 样本数不足时直接为每条轨迹分配独立人物 ID
        if len(valid_tracks) < self.config.min_samples:
            for index, track in enumerate(valid_tracks):
                track.person_id = index
            return tracks

        embeddings = normalize(np.vstack([track.embedding for track in valid_tracks]))
        labels = DBSCAN(
            eps=self.config.eps,
            min_samples=min(self.config.min_samples, len(valid_tracks)),
            metric="cosine",
        ).fit_predict(embeddings)

        # DBSCAN 中 label < 0 表示噪声，为噪声轨迹分配独立编号
        next_noise_id = 1 + max((int(label) for label in labels if label >= 0), default=-1)
        for track, label in zip(valid_tracks, labels, strict=True):
            if label < 0:
                track.person_id = next_noise_id
                next_noise_id += 1
            else:
                track.person_id = int(label)

        return tracks

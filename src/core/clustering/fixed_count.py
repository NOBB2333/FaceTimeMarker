from __future__ import annotations

import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize

from core.models import FaceTrack


def assign_fixed_person_count(tracks: list[FaceTrack], expected_people_count: int) -> bool:
    """按预设人物数量对轨迹做固定数量聚类，成功处理返回 True。"""
    valid_tracks = [track for track in tracks if track.embedding is not None]
    if not valid_tracks or expected_people_count <= 0:
        return False

    cluster_count = min(expected_people_count, len(valid_tracks))
    if cluster_count == 1:
        for track in valid_tracks:
            track.person_id = 0
        return True

    embeddings = normalize(np.vstack([track.embedding for track in valid_tracks]))
    labels = KMeans(
        n_clusters=cluster_count,
        random_state=0,
        n_init="auto",
    ).fit_predict(embeddings)
    for track, label in zip(valid_tracks, labels, strict=True):
        track.person_id = int(label)
    return True

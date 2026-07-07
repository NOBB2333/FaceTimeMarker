import numpy as np

from core.clustering.hdbscan_clusterer import HdbscanFaceClusterer
from core.config import ClusteringConfig
from core.models import FaceTrack


def test_hdbscan_assigns_person_ids() -> None:
    """验证 HdbscanFaceClusterer 能根据嵌入向量将相近轨迹聚为同一人。"""
    tracks = [
        FaceTrack(track_id=1, embedding=np.array([1.0, 0.0])),
        FaceTrack(track_id=2, embedding=np.array([0.99, 0.01])),
        FaceTrack(track_id=3, embedding=np.array([0.0, 1.0])),
        FaceTrack(track_id=4, embedding=np.array([0.01, 0.99])),
    ]

    clusterer = HdbscanFaceClusterer(ClusteringConfig(min_cluster_size=2, min_samples=1))
    result = clusterer.assign_person_ids(tracks)

    # 前两条嵌入接近，应归为同一人；后两条归为另一人
    assert result[0].person_id == result[1].person_id
    assert result[2].person_id == result[3].person_id
    assert result[0].person_id != result[2].person_id


def test_hdbscan_respects_expected_people_count() -> None:
    """验证预设人物数量时会用固定数量聚类，而不是自动噪声拆分。"""
    tracks = [
        FaceTrack(track_id=1, embedding=np.array([1.0, 0.0])),
        FaceTrack(track_id=2, embedding=np.array([0.98, 0.02])),
        FaceTrack(track_id=3, embedding=np.array([0.0, 1.0])),
        FaceTrack(track_id=4, embedding=np.array([0.02, 0.98])),
    ]

    clusterer = HdbscanFaceClusterer(
        ClusteringConfig(expected_people_count=2, min_cluster_size=3, min_samples=3)
    )
    result = clusterer.assign_person_ids(tracks)

    person_ids = {track.person_id for track in result}
    assert len(person_ids) == 2
    assert result[0].person_id == result[1].person_id
    assert result[2].person_id == result[3].person_id
    assert result[0].person_id != result[2].person_id


def test_hdbscan_expected_people_count_one_groups_all_tracks() -> None:
    """验证预设 1 人时所有有效轨迹都会归为同一个人物。"""
    tracks = [
        FaceTrack(track_id=1, embedding=np.array([1.0, 0.0])),
        FaceTrack(track_id=2, embedding=np.array([0.0, 1.0])),
    ]

    clusterer = HdbscanFaceClusterer(ClusteringConfig(expected_people_count=1))
    result = clusterer.assign_person_ids(tracks)

    assert [track.person_id for track in result] == [0, 0]

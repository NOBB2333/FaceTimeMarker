from pathlib import Path

import numpy as np

from adapters.identity.store import IdentityStore
from core.models import PersonSummary, VideoInfo


def test_identity_store_matches_same_embedding_across_videos(tmp_path: Path) -> None:
    """验证 IdentityStore 能跨视频匹配相同人脸，并分配一致的全局人物 ID。"""
    store_path = tmp_path / "people_index.json"
    first_video = VideoInfo(Path("movie_a.mp4"), fps=24.0, frame_count=240, width=640, height=360)
    second_video = VideoInfo(Path("movie_b.mp4"), fps=24.0, frame_count=240, width=640, height=360)

    # 首次分配：在 movie_a 中出现第一个人物
    store = IdentityStore.load(store_path, match_threshold=0.8)
    first_people = store.assign([_person(0, np.array([1.0, 0.0]))], first_video)
    store.save()

    # 重新加载 store 后在 movie_b 中分配相似嵌入，应命中已有全局人物
    store = IdentityStore.load(store_path, match_threshold=0.8)
    second_people = store.assign([_person(0, np.array([0.99, 0.01]))], second_video)
    store.save()

    payload = store_path.read_text(encoding="utf-8")
    assert first_people[0].global_person_id == "global_person_000001"
    assert second_people[0].global_person_id == "global_person_000001"
    assert payload.count("movie_a.mp4") == 1
    assert payload.count("movie_b.mp4") == 1


def test_identity_store_confirms_and_rejects_observations(tmp_path: Path) -> None:
    """验证 IdentityStore 的确认与驳回观察会正确更新全局人物索引状态。"""
    store_path = tmp_path / "people_index.json"
    video = VideoInfo(Path("movie_a.mp4"), fps=24.0, frame_count=240, width=640, height=360)
    store = IdentityStore.load(store_path, match_threshold=0.8)
    assigned = store.assign([_person(0, np.array([1.0, 0.0]))], video)
    global_person_id = assigned[0].global_person_id
    assert global_person_id is not None

    # 确认观察后保存，索引中应记录 confirmed 为 true
    store.confirm_observation(global_person_id, "movie_a.mp4", 0)
    store.save()
    payload = store_path.read_text(encoding="utf-8")
    assert '"confirmed": true' in payload

    # 驳回观察应创建新的全局人物，并将原观察加入 rejected_matches
    new_global_person_id = store.reject_observation(global_person_id, "movie_a.mp4", 0)
    store.save()

    assert new_global_person_id != global_person_id
    assert len(store.people) == 2
    assert store.people[0].rejected_matches == ["movie_a.mp4#0"]


def _person(person_id: int, embedding: np.ndarray) -> PersonSummary:
    """辅助函数：根据 person_id 和嵌入向量构造 PersonSummary。"""
    return PersonSummary(
        person_id=person_id,
        label=f"person_{person_id + 1:03d}",
        track_ids=(person_id,),
        appearances=1,
        total_duration=1.0,
        detection_count=2,
        embedding=embedding,
    )

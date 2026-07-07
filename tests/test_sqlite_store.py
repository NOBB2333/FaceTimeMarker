from __future__ import annotations

import json
from pathlib import Path

from core.storage import SQLiteStore
from core.storage.database import session_scope
from core.storage.orm_models import FaceCropRow


def test_sqlite_store_imports_review_data_and_updates_people(tmp_path: Path) -> None:
    """验证 SQLiteStore 导入时间线、更新审阅数据，并支持人员确认/拆分/合并/删除。"""
    timeline_path = tmp_path / "timeline.json"
    timeline_path.write_text(
        json.dumps(
            {
                "video": {
                    "path": "movie.mp4",
                    "fps": 25.0,
                    "frame_count": 250,
                    "width": 1920,
                    "height": 1080,
                },
                "diagnostics": {"sampled_frames": 10},
                "people_count": 2,
                "people": [
                    {
                        "person_id": 0,
                        "label": "person_001",
                        "global_person_id": "global_person_000001",
                        "track_ids": [11, 12],
                        "appearances": 2,
                        "total_duration": 4.0,
                        "detection_count": 5,
                        "representative_face_path": "faces/person_001.jpg",
                        "representative_timestamp": 1.0,
                        "representative_frame_index": 25,
                    },
                    {
                        "person_id": 1,
                        "label": "person_002",
                        "global_person_id": "global_person_000002",
                        "track_ids": [21],
                        "appearances": 1,
                        "total_duration": 1.5,
                        "detection_count": 2,
                        "representative_face_path": "faces/person_002.jpg",
                    },
                ],
                "tracks": [
                    _track(11, 0, 1.0, 2.0, "faces/track_011.jpg"),
                    _track(12, 0, 5.0, 6.0, "faces/track_012.jpg"),
                    _track(21, 1, 7.0, 8.5, "faces/track_021.jpg"),
                ],
                "persons": {
                    "0": [
                        _segment(0, 1.0, 2.0, [11]),
                        _segment(0, 5.0, 6.0, [12]),
                    ],
                    "1": [_segment(1, 7.0, 8.5, [21])],
                },
            }
        ),
        encoding="utf-8",
    )

    store = SQLiteStore(tmp_path / "facetimemarker.db")
    video_id = store.import_timeline(timeline_path)

    # 校验导入后的基础统计
    imported_video = store.get_video(video_id)
    assert imported_video is not None
    assert imported_video["title"] == "movie"
    assert imported_video["original_filename"] == "movie.mp4"
    assert imported_video["source_path"] == "movie.mp4"
    assert imported_video["source_directory"] == "."
    assert len(store.list_tracks(video_id)) == 3
    face_crops = store.list_face_crops(video_id)
    assert len(face_crops) == 4
    assert len(store.list_track_detections(video_id)) == 6
    assert store.list_track_detections(video_id, track_id=11)[0]["bbox_json"] == "[1, 2, 3, 4]"
    assert any(item["track_id"] == 11 and item["bbox_json"] == "[1, 2, 3, 4]" for item in face_crops)
    assert len(store.list_global_people()) == 2
    assert len(store.list_global_observations("global_person_000001")) == 1

    # 视频作品信息可用于批量视频分组和列表检索展示
    updated_video = store.update_video_metadata(
        video_id,
        title="第一集",
        series_name="测试系列",
        original_filename="movie-original.mp4",
        source_path="/media/drama/movie-original.mp4",
    )
    assert updated_video["title"] == "第一集"
    assert updated_video["series_name"] == "测试系列"
    assert updated_video["original_filename"] == "movie-original.mp4"
    assert updated_video["source_path"] == "/media/drama/movie-original.mp4"
    assert updated_video["source_directory"] == "/media/drama"

    # 确认与驳回全局观察
    store.confirm_global_observation("global_person_000001", "movie.mp4", 0)
    confirmed = store.list_global_observations("global_person_000001")[0]
    assert confirmed["confirmed"] == 1
    assert store.list_global_people()[0]["confirmed_count"] == 1

    store.reject_global_observation(
        "global_person_000001",
        "movie.mp4",
        0,
        "global_person_999999",
    )
    moved = store.list_global_observations("global_person_999999")[0]
    assert moved["confirmed"] == 1
    assert moved["local_person_id"] == 0

    # 可以把某一集的人物手动关联到已有全局人物档案
    store.link_person_to_global(video_id, 0, "global_person_000002")
    linked_people = store.list_people(video_id)
    assert linked_people[0]["global_person_id"] == "global_person_000002"
    assert store.list_global_observations("global_person_999999") == []
    linked_observations = store.list_global_observations("global_person_000002")
    assert {item["local_person_id"] for item in linked_observations} == {0, 1}
    assert all(item["series_name"] == "测试系列" for item in linked_observations)

    # 重命名、拆分、合并、删除人员
    store.rename_person(video_id, 0, "主角")
    assert store.list_people(video_id)[0]["label"] == "主角"

    new_person_id = store.split_tracks_to_person(video_id, 0, [12], label="侧脸")
    assert new_person_id == 2
    assert [person["person_id"] for person in store.list_people(video_id)] == [0, 1, 2]
    assert store.list_tracks(video_id, person_id=2)[0]["track_id"] == 12
    assert {row["person_id"] for row in store.list_track_detections(video_id, track_id=12)} == {2}

    store.merge_people(video_id, source_person_id=2, target_person_id=1)
    people = store.list_people(video_id)
    assert [person["person_id"] for person in people] == [0, 1]
    assert len(store.list_tracks(video_id, person_id=1)) == 2
    assert {row["person_id"] for row in store.list_track_detections(video_id, track_id=12)} == {1}

    store.assign_tracks_to_person(video_id, [11], target_person_id=1)
    people = store.list_people(video_id)
    assert [person["person_id"] for person in people] == [1]
    assert sorted(track["track_id"] for track in store.list_tracks(video_id, person_id=1)) == [
        11,
        12,
        21,
    ]
    assert {row["person_id"] for row in store.list_track_detections(video_id, track_id=11)} == {1}

    store.delete_tracks(video_id, [11])
    assert sorted(track["track_id"] for track in store.list_tracks(video_id, person_id=1)) == [
        12,
        21,
    ]
    assert store.list_track_detections(video_id, track_id=11) == []
    assert all(11 not in json.loads(segment["track_ids"]) for segment in store.list_segments(video_id))

    store.delete_person(video_id, 1)
    assert store.list_people(video_id) == []
    assert store.list_track_detections(video_id) == []
    assert store.list_videos()[0]["people_count"] == 0


def test_sqlite_store_dedupes_same_frame_face_crop_candidates(tmp_path: Path) -> None:
    """验证同一人物同一帧的代表脸候选不会重复返回给前端。"""
    timeline_path = tmp_path / "timeline.json"
    timeline_path.write_text(
        json.dumps(
            {
                "video": {
                    "path": "movie.mp4",
                    "fps": 25.0,
                    "frame_count": 250,
                    "width": 1920,
                    "height": 1080,
                },
                "people_count": 1,
                "people": [
                    {
                        "person_id": 0,
                        "label": "person_001",
                        "global_person_id": "global_person_000001",
                        "track_ids": [11],
                        "appearances": 1,
                        "total_duration": 1.0,
                        "detection_count": 2,
                        "representative_face_path": "faces/person_001.jpg",
                        "representative_timestamp": 1.0,
                        "representative_frame_index": 25,
                    }
                ],
                "tracks": [_track(11, 0, 1.0, 2.0, "faces/person_001.jpg")],
                "persons": {"0": [_segment(0, 1.0, 2.0, [11])]},
            }
        ),
        encoding="utf-8",
    )

    store = SQLiteStore(tmp_path / "facetimemarker.db")
    video_id = store.import_timeline(timeline_path)

    imported_crops = store.list_face_crops(video_id, person_id=0)
    assert len(imported_crops) == 1
    assert imported_crops[0]["source"] == "track_representative"
    assert imported_crops[0]["frame_index"] == 25

    with session_scope(store.session_factory) as session:
        session.add(
            FaceCropRow(
                video_id=video_id,
                person_id=0,
                track_id=None,
                path="faces/person_001.jpg",
                source="person_representative",
                confidence=None,
                timestamp=1.0,
                frame_index=25,
            )
        )

    existing_crops = store.list_face_crops(video_id, person_id=0)
    assert len(existing_crops) == 1
    assert existing_crops[0]["source"] == "track_representative"
    assert existing_crops[0]["frame_index"] == 25


def test_sqlite_store_hides_people_from_default_views(tmp_path: Path) -> None:
    """验证隐藏人物不会删除数据，但默认视图和搜索会过滤它。"""
    timeline_path = tmp_path / "timeline.json"
    timeline_path.write_text(
        json.dumps(
            {
                "video": {
                    "path": "episode_01.mp4",
                    "fps": 25.0,
                    "frame_count": 250,
                    "width": 1920,
                    "height": 1080,
                },
                "people_count": 1,
                "people": [
                    {
                        "person_id": 0,
                        "label": "路人甲",
                        "global_person_id": "global_person_000001",
                        "track_ids": [11],
                        "appearances": 1,
                        "total_duration": 1.0,
                        "detection_count": 2,
                        "representative_face_path": "faces/person_001.jpg",
                    }
                ],
                "tracks": [_track(11, 0, 1.0, 2.0, "faces/track_011.jpg")],
                "persons": {"0": [_segment(0, 1.0, 2.0, [11])]},
            }
        ),
        encoding="utf-8",
    )

    store = SQLiteStore(tmp_path / "facetimemarker.db")
    video_id = store.import_timeline(timeline_path)

    assert store.list_videos()[0]["people_count"] == 1
    assert len(store.search_people("路人甲")) == 1

    store.set_person_hidden(video_id, 0, True)

    hidden_people = store.list_people(video_id)
    assert hidden_people[0]["hidden"] == 1
    assert store.list_videos()[0]["people_count"] == 0
    assert store.search_people("路人甲") == []
    assert store.list_global_people() == []
    assert store.list_global_observations("global_person_000001") == []
    hidden_observations = store.list_global_observations(
        "global_person_000001",
        include_hidden=True,
    )
    assert hidden_observations[0]["hidden"] == 1

    store.set_person_hidden(video_id, 0, False)

    assert store.list_people(video_id)[0]["hidden"] == 0
    assert store.list_videos()[0]["people_count"] == 1
    assert len(store.search_people("路人甲")) == 1


def test_sqlite_store_manual_profile_and_four_view_assets(tmp_path: Path) -> None:
    """验证人物档案可以脱离视频手动创建，并登记四视图原图资产。"""
    store = SQLiteStore(tmp_path / "facetimemarker.db")

    global_person_id = store.create_manual_global_person("手动角色")
    people = store.list_global_people()

    assert len(people) == 1
    assert people[0]["global_person_id"] == global_person_id
    assert people[0]["label"] == "手动角色"
    assert people[0]["observation_count"] == 0
    assert people[0]["four_view_asset_count"] == 0

    asset = store.add_four_view_asset(
        global_person_id,
        image_path=str(tmp_path / "four-view.png"),
        label="第一套服装",
    )
    second_asset = store.add_four_view_asset(
        global_person_id,
        image_path=str(tmp_path / "four-view-2.png"),
        label="第二套服装",
    )
    assets = store.list_four_view_assets(global_person_id)
    people = store.list_global_people()

    assert asset["label"] == "第一套服装"
    assert assets[0]["image_path"].endswith("four-view-2.png")
    assert people[0]["representative_face_path"].endswith("four-view.png")
    assert people[0]["four_view_asset_count"] == 2

    deleted = store.delete_four_view_asset(global_person_id, asset["id"])
    assets = store.list_four_view_assets(global_person_id)
    people = store.list_global_people()

    assert deleted["id"] == asset["id"]
    assert [item["id"] for item in assets] == [second_asset["id"]]
    assert people[0]["representative_face_path"].endswith("four-view-2.png")
    assert people[0]["four_view_asset_count"] == 1

    target_global_person_id = store.create_manual_global_person("拆分角色")
    moved = store.move_four_view_assets(global_person_id, target_global_person_id)
    source_assets = store.list_four_view_assets(global_person_id)
    target_assets = store.list_four_view_assets(target_global_person_id)
    people_by_id = {item["global_person_id"]: item for item in store.list_global_people(include_hidden=True)}

    assert [item["id"] for item in moved["moved_assets"]] == [second_asset["id"]]
    assert source_assets == []
    assert [item["id"] for item in target_assets] == [second_asset["id"]]
    assert people_by_id[global_person_id]["four_view_asset_count"] == 0
    assert people_by_id[target_global_person_id]["four_view_asset_count"] == 1


def test_sqlite_store_assign_tracks_rejects_missing_track(tmp_path: Path) -> None:
    """验证批量归类轨迹时，不存在的 track 会被拒绝。"""
    timeline_path = tmp_path / "timeline.json"
    timeline_path.write_text(
        json.dumps(
            {
                "video": {
                    "path": "movie.mp4",
                    "fps": 25.0,
                    "frame_count": 250,
                    "width": 1920,
                    "height": 1080,
                },
                "people_count": 1,
                "people": [
                    {
                        "person_id": 0,
                        "label": "person_001",
                        "global_person_id": None,
                        "track_ids": [11],
                        "appearances": 1,
                        "total_duration": 1.0,
                        "detection_count": 2,
                        "representative_face_path": "faces/person_001.jpg",
                    }
                ],
                "tracks": [_track(11, 0, 1.0, 2.0, "faces/track_011.jpg")],
                "persons": {"0": [_segment(0, 1.0, 2.0, [11])]},
            }
        ),
        encoding="utf-8",
    )

    store = SQLiteStore(tmp_path / "facetimemarker.db")
    video_id = store.import_timeline(timeline_path)

    try:
        store.assign_tracks_to_person(video_id, [99], target_person_id=0)
    except ValueError as exc:
        assert "tracks not found" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("assign_tracks_to_person should reject missing tracks")


def test_sqlite_store_assign_tracks_rejects_missing_target(tmp_path: Path) -> None:
    """验证批量归类轨迹时，目标人物不存在会被拒绝。"""
    timeline_path = tmp_path / "timeline.json"
    timeline_path.write_text(
        json.dumps(
            {
                "video": {
                    "path": "movie.mp4",
                    "fps": 25.0,
                    "frame_count": 250,
                    "width": 1920,
                    "height": 1080,
                },
                "people_count": 1,
                "people": [
                    {
                        "person_id": 0,
                        "label": "person_001",
                        "global_person_id": None,
                        "track_ids": [11],
                        "appearances": 1,
                        "total_duration": 1.0,
                        "detection_count": 2,
                        "representative_face_path": "faces/person_001.jpg",
                    }
                ],
                "tracks": [_track(11, 0, 1.0, 2.0, "faces/track_011.jpg")],
                "persons": {"0": [_segment(0, 1.0, 2.0, [11])]},
            }
        ),
        encoding="utf-8",
    )

    store = SQLiteStore(tmp_path / "facetimemarker.db")
    video_id = store.import_timeline(timeline_path)

    try:
        store.assign_tracks_to_person(video_id, [11], target_person_id=9)
    except ValueError as exc:
        assert "person not found" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("assign_tracks_to_person should reject missing target")


def test_sqlite_store_backfills_tracks_from_legacy_segments(tmp_path: Path) -> None:
    """验证旧版时间线没有 tracks 字段时，SQLiteStore 可从 persons 段反推轨迹。"""
    timeline_path = tmp_path / "legacy_timeline.json"
    timeline_path.write_text(
        json.dumps(
            {
                "video": {
                    "path": "legacy.mp4",
                    "fps": 25.0,
                    "frame_count": 250,
                    "width": 1920,
                    "height": 1080,
                },
                "people_count": 1,
                "people": [
                    {
                        "person_id": 0,
                        "label": "person_001",
                        "global_person_id": None,
                        "track_ids": [7],
                        "appearances": 1,
                        "total_duration": 1.0,
                        "detection_count": 3,
                        "representative_face_path": None,
                    }
                ],
                "persons": {"0": [_segment(0, 3.0, 4.0, [7])]},
            }
        ),
        encoding="utf-8",
    )

    store = SQLiteStore(tmp_path / "facetimemarker.db")
    video_id = store.import_timeline(timeline_path)

    tracks = store.list_tracks(video_id)
    assert len(tracks) == 1
    assert tracks[0]["track_id"] == 7
    assert tracks[0]["person_id"] == 0


def test_sqlite_store_moves_videos_to_trash_and_restores(tmp_path: Path) -> None:
    """验证素材可以移入回收站、还原，并在彻底删除时清理关联数据。"""
    timeline_path = tmp_path / "trash_timeline.json"
    timeline_path.write_text(
        json.dumps(
            {
                "video": {
                    "path": "trash.mp4",
                    "fps": 25.0,
                    "frame_count": 250,
                    "width": 1920,
                    "height": 1080,
                },
                "people_count": 1,
                "people": [
                    {
                        "person_id": 0,
                        "label": "person_001",
                        "global_person_id": "global_person_000001",
                        "track_ids": [11],
                        "appearances": 1,
                        "total_duration": 1.0,
                        "detection_count": 2,
                        "representative_face_path": "faces/person_001.jpg",
                    }
                ],
                "tracks": [_track(11, 0, 1.0, 2.0, "faces/track_011.jpg")],
                "persons": {"0": [_segment(0, 1.0, 2.0, [11])]},
            }
        ),
        encoding="utf-8",
    )
    store = SQLiteStore(tmp_path / "facetimemarker.db")
    video_id = store.import_timeline(timeline_path)

    trashed = store.move_video_to_trash(video_id)

    assert trashed["deleted_at"] is not None
    assert store.list_videos() == []
    assert store.list_videos(only_deleted=True)[0]["id"] == video_id
    assert store.list_global_people() == []

    restored = store.restore_video(video_id)

    assert restored["deleted_at"] is None
    assert store.list_videos()[0]["id"] == video_id
    assert len(store.list_global_people()) == 1

    store.move_video_to_trash(video_id)
    store.purge_video(video_id)

    assert store.list_videos(include_deleted=True) == []
    assert store.list_people(video_id) == []
    assert store.list_global_observations("global_person_000001", include_hidden=True) == []


def test_sqlite_store_deletes_and_merges_global_people(tmp_path: Path) -> None:
    """验证人物档案合并、回收站、恢复和彻底删除会同步处理关联数据。"""
    timeline_path = tmp_path / "profiles.json"
    timeline_path.write_text(
        json.dumps(
            {
                "video": {
                    "path": "profiles.mp4",
                    "fps": 25.0,
                    "frame_count": 250,
                    "width": 1280,
                    "height": 720,
                },
                "people_count": 2,
                "people": [
                    {
                        "person_id": 0,
                        "label": "主角A",
                        "global_person_id": "global_person_000001",
                        "track_ids": [11],
                        "appearances": 1,
                        "total_duration": 2.0,
                        "detection_count": 3,
                        "representative_face_path": "faces/person_001.jpg",
                        "representative_timestamp": 1.0,
                        "representative_frame_index": 25,
                    },
                    {
                        "person_id": 1,
                        "label": "主角B",
                        "global_person_id": "global_person_000002",
                        "track_ids": [21],
                        "appearances": 1,
                        "total_duration": 3.0,
                        "detection_count": 4,
                        "representative_face_path": "faces/person_002.jpg",
                        "representative_timestamp": 4.0,
                        "representative_frame_index": 100,
                    },
                ],
                "tracks": [
                    _track(11, 0, 1.0, 2.0, "faces/track_011.jpg"),
                    _track(21, 1, 4.0, 5.0, "faces/track_021.jpg"),
                ],
                "persons": {
                    "0": [_segment(0, 1.0, 2.0, [11])],
                    "1": [_segment(1, 4.0, 5.0, [21])],
                },
            }
        ),
        encoding="utf-8",
    )
    store = SQLiteStore(tmp_path / "facetimemarker.db")
    video_id = store.import_timeline(timeline_path)
    store.add_four_view_asset("global_person_000002", image_path="assets/four-view.png", label="误建四视图")

    store.rename_global_person("global_person_000001", "正式主角")
    renamed = store.list_global_people(include_hidden=True)[0]
    assert renamed["label"] == "正式主角"

    store.merge_global_people("global_person_000002", "global_person_000001")

    people = store.list_global_people(include_hidden=True)
    assert [person["global_person_id"] for person in people] == ["global_person_000001"]
    assert people[0]["label"] == "正式主角"
    assert people[0]["observation_count"] == 2
    local_people = store.list_people(video_id)
    observations = store.list_global_observations("global_person_000001", True)
    assert {person["global_person_id"] for person in local_people} == {"global_person_000001"}
    assert local_people[0]["representative_timestamp"] == 1.0
    assert local_people[0]["representative_frame_index"] == 25
    assert {item["local_person_id"] for item in observations} == {0, 1}
    assert {item["representative_timestamp"] for item in observations} == {1.0, 4.0}
    assert store.list_four_view_assets("global_person_000001")[0]["image_path"] == "assets/four-view.png"

    store.delete_global_person("global_person_000001")

    assert store.list_global_people(include_hidden=True) == []
    deleted_people = store.list_global_people(include_hidden=True, only_deleted=True)
    assert deleted_people[0]["global_person_id"] == "global_person_000001"
    assert deleted_people[0]["deleted_at"] is not None
    assert deleted_people[0]["observation_count"] == 2
    assert {item["local_person_id"] for item in store.list_global_observations("global_person_000001", True)} == {0, 1}
    assert {person["global_person_id"] for person in store.list_people(video_id)} == {"global_person_000001"}
    assert store.list_four_view_assets("global_person_000001")[0]["image_path"] == "assets/four-view.png"

    store.restore_global_person("global_person_000001")

    restored_people = store.list_global_people(include_hidden=True)
    assert restored_people[0]["global_person_id"] == "global_person_000001"
    assert restored_people[0]["deleted_at"] is None
    assert store.list_global_people(include_hidden=True, only_deleted=True) == []

    store.delete_global_person("global_person_000001")
    store.purge_global_person("global_person_000001")

    assert store.list_global_people(include_hidden=True, include_deleted=True) == []
    assert store.list_global_observations("global_person_000001", include_hidden=True) == []
    assert all(person["global_person_id"] is None for person in store.list_people(video_id))
    actions = store.list_global_person_actions("global_person_000001")
    assert {
        "rename_profile",
        "merge_profile",
        "trash_profile",
        "restore_profile",
        "purge_profile",
    }.issubset({action["action"] for action in actions})


def _track(
    track_id: int,
    person_id: int,
    start: float,
    end: float,
    face_path: str,
) -> dict:
    """辅助函数：构造一条 track 的字典表示。"""
    return {
        "track_id": track_id,
        "person_id": person_id,
        "start": start,
        "end": end,
        "detection_count": 2,
        "representative_face_path": face_path,
        "representative_bbox": [1, 2, 3, 4],
        "representative_confidence": 0.95,
        "representative_timestamp": start,
        "representative_frame_index": int(start * 25),
        "detections": [
            {
                "frame_index": int(start * 25),
                "timestamp": start,
                "bbox": [1, 2, 3, 4],
                "confidence": 0.95,
            },
            {
                "frame_index": int(end * 25),
                "timestamp": end,
                "bbox": [2, 3, 4, 5],
                "confidence": 0.9,
            },
        ],
        "embedding_dim": 512,
        "embedding_norm": 1.0,
    }


def _segment(person_id: int, start: float, end: float, track_ids: list[int]) -> dict:
    """辅助函数：构造一个时间段的字典表示。"""
    return {
        "person_id": person_id,
        "start": start,
        "end": end,
        "track_ids": track_ids,
        "detection_count": 2,
        "clip_path": None,
    }

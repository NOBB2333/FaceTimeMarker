from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from core.models import PersonSummary, VideoInfo


@dataclass
class PersonObservation:
    """某个人物在单个视频中的出现记录。"""

    video_path: str  # 视频文件路径
    local_person_id: int  # 该视频内的人物 ID
    label: str  # 人物标签
    representative_face_path: str | None  # 代表人脸截图路径
    appearances: int  # 出现片段数
    total_duration: float  # 总出现时长（秒）
    detection_count: int  # 总检测次数
    confirmed: bool = False  # 是否经过人工确认


@dataclass
class GlobalPerson:
    """跨视频全局人物。"""

    global_person_id: str  # 全局唯一人物 ID
    embedding: np.ndarray  # 聚合后的人脸特征向量
    # 该人物在各视频中的观测记录
    observations: list[PersonObservation] = field(default_factory=list)
    rejected_matches: list[str] = field(default_factory=list)  # 被人工拒绝匹配的观测 key


class IdentityStore:
    """跨视频人物身份库，支持加载、匹配与保存。"""

    def __init__(self, path: Path, match_threshold: float) -> None:
        """初始化人物库。"""
        self.path = path
        self.match_threshold = match_threshold
        self.people: list[GlobalPerson] = []

    @classmethod
    def load(cls, path: Path, match_threshold: float) -> IdentityStore:
        """从 JSON 文件加载人物库，文件不存在则返回空库。"""
        store = cls(path=path, match_threshold=match_threshold)
        if not path.exists():
            return store

        payload = json.loads(path.read_text(encoding="utf-8"))
        store.people = [
            GlobalPerson(
                global_person_id=item["global_person_id"],
                embedding=_normalize(np.array(item["embedding"], dtype=np.float32)),
                observations=[
                    PersonObservation(
                        video_path=observation["video_path"],
                        local_person_id=int(observation["local_person_id"]),
                        label=observation["label"],
                        representative_face_path=observation.get("representative_face_path"),
                        appearances=int(observation["appearances"]),
                        total_duration=float(observation["total_duration"]),
                        detection_count=int(observation.get("detection_count", 0)),
                        confirmed=bool(observation.get("confirmed", False)),
                    )
                    for observation in item.get("observations", [])
                ],
                rejected_matches=list(item.get("rejected_matches", [])),
            )
            for item in payload.get("people", [])
        ]
        return store

    def save(self) -> None:
        """将人物库持久化到 JSON 文件。"""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "match_threshold": self.match_threshold,
            "people_count": len(self.people),
            "people": [self._person_to_json(person) for person in self.people],
        }
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def assign(self, people: list[PersonSummary], video: VideoInfo) -> list[PersonSummary]:
        """将当前视频的人物与全局人物库匹配，更新库并回写 global_person_id。"""
        assigned: list[PersonSummary] = []
        for person in people:
            if person.embedding is None:
                assigned.append(person)
                continue

            embedding = _normalize(person.embedding)
            observation_key = _observation_key(str(video.path), person.person_id)
            global_person = self._find_match(embedding, observation_key)
            if global_person is None:
                # 未匹配到已有全局人物，则新建一条全局记录
                global_person = GlobalPerson(
                    global_person_id=self._next_global_person_id(),
                    embedding=embedding,
                )
                self.people.append(global_person)
            else:
                # 匹配成功，更新全局 embedding 为二者平均并归一化
                global_person.embedding = _normalize((global_person.embedding + embedding) / 2.0)

            observation = PersonObservation(
                video_path=str(video.path),
                local_person_id=person.person_id,
                label=person.label,
                representative_face_path=(
                    str(person.representative_face_path)
                    if person.representative_face_path is not None
                    else None
                ),
                appearances=person.appearances,
                total_duration=person.total_duration,
                detection_count=person.detection_count,
                confirmed=False,
            )
            _upsert_observation(global_person.observations, observation)
            assigned.append(
                PersonSummary(
                    person_id=person.person_id,
                    label=person.label,
                    track_ids=person.track_ids,
                    appearances=person.appearances,
                    total_duration=person.total_duration,
                    detection_count=person.detection_count,
                    representative_face_path=person.representative_face_path,
                    representative_timestamp=person.representative_timestamp,
                    representative_frame_index=person.representative_frame_index,
                    embedding=person.embedding,
                    global_person_id=global_person.global_person_id,
                )
            )

        return assigned

    def confirm_observation(
        self,
        global_person_id: str,
        video_path: str,
        local_person_id: int,
    ) -> None:
        """人工确认某个视频人物属于指定全局人物。"""
        person = self._require_global_person(global_person_id)
        observation = _find_observation(person.observations, video_path, local_person_id)
        if observation is None:
            raise ValueError("observation not found")
        observation.confirmed = True
        key = _observation_key(video_path, local_person_id)
        person.rejected_matches = [item for item in person.rejected_matches if item != key]

    def reject_observation(
        self,
        global_person_id: str,
        video_path: str,
        local_person_id: int,
    ) -> str:
        """人工拒绝某个视频人物与当前全局人物的匹配，并返回新全局人物 ID。"""
        person = self._require_global_person(global_person_id)
        observation = _find_observation(person.observations, video_path, local_person_id)
        if observation is None:
            raise ValueError("observation not found")
        person.observations = [
            item
            for item in person.observations
            if not (item.video_path == video_path and item.local_person_id == local_person_id)
        ]
        key = _observation_key(video_path, local_person_id)
        if key not in person.rejected_matches:
            person.rejected_matches.append(key)

        new_person = GlobalPerson(
            global_person_id=self._next_global_person_id(),
            embedding=np.copy(person.embedding),
            observations=[
                PersonObservation(
                    video_path=observation.video_path,
                    local_person_id=observation.local_person_id,
                    label=observation.label,
                    representative_face_path=observation.representative_face_path,
                    appearances=observation.appearances,
                    total_duration=observation.total_duration,
                    detection_count=observation.detection_count,
                    confirmed=True,
                )
            ],
        )
        self.people.append(new_person)
        return new_person.global_person_id

    def _find_match(self, embedding: np.ndarray, observation_key: str) -> GlobalPerson | None:
        """在全局人物库中寻找与 embedding 余弦相似度最高且超过阈值的人物。"""
        best: tuple[float, GlobalPerson] | None = None
        for person in self.people:
            if observation_key in person.rejected_matches:
                continue
            similarity = float(np.dot(person.embedding, embedding))
            if best is None or similarity > best[0]:
                best = (similarity, person)
        if best is None or best[0] < self.match_threshold:
            return None
        return best[1]

    def _next_global_person_id(self) -> str:
        """生成下一个可用的全局人物 ID。"""
        existing = {person.global_person_id for person in self.people}
        index = 1
        while True:
            candidate = f"global_person_{index:06d}"
            if candidate not in existing:
                return candidate
            index += 1

    def _require_global_person(self, global_person_id: str) -> GlobalPerson:
        """断言指定全局人物存在并返回。"""
        for person in self.people:
            if person.global_person_id == global_person_id:
                return person
        raise ValueError(f"global person not found: {global_person_id}")

    @staticmethod
    def _person_to_json(person: GlobalPerson) -> dict[str, Any]:
        """将 GlobalPerson 序列化为字典。"""
        return {
            "global_person_id": person.global_person_id,
            "embedding": [float(value) for value in person.embedding],
            "rejected_matches": person.rejected_matches,
            "observations": [
                {
                    "video_path": observation.video_path,
                    "local_person_id": observation.local_person_id,
                    "label": observation.label,
                    "representative_face_path": observation.representative_face_path,
                    "appearances": observation.appearances,
                    "total_duration": round(observation.total_duration, 3),
                    "detection_count": observation.detection_count,
                    "confirmed": observation.confirmed,
                }
                for observation in person.observations
            ],
        }


def _upsert_observation(
    observations: list[PersonObservation],
    observation: PersonObservation,
) -> None:
    """如果同一视频同一人物已存在观测则更新，否则追加。"""
    for index, existing in enumerate(observations):
        if (
            existing.video_path == observation.video_path
            and existing.local_person_id == observation.local_person_id
        ):
            observations[index] = observation
            return
    observations.append(observation)


def _find_observation(
    observations: list[PersonObservation],
    video_path: str,
    local_person_id: int,
) -> PersonObservation | None:
    """在观测列表中查找指定视频和本地人物 ID 的观测。"""
    for observation in observations:
        if observation.video_path == video_path and observation.local_person_id == local_person_id:
            return observation
    return None


def _observation_key(video_path: str, local_person_id: int) -> str:
    """生成观测的唯一标识 key。"""
    return f"{video_path}#{local_person_id}"


def _normalize(embedding: np.ndarray) -> np.ndarray:
    """对 embedding 做 L2 归一化。"""
    norm = np.linalg.norm(embedding)
    if norm <= 0:
        return embedding.astype(np.float32)
    return (embedding / norm).astype(np.float32)

from __future__ import annotations

import base64
import json
import queue
import shutil
import tempfile
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import cv2
import litellm
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field, field_validator

from adapters.face.insightface_analyzer import InsightFaceAnalyzer
from adapters.identity.store import IdentityStore
from core.config import PRESET_NAMES, apply_preset, load_config
from core.hardware import hardware_summary
from core.models import Frame
from core.pipeline import FaceVideoPipeline, PipelineCancelled
from core.storage import ResultStore
from core.timeline.context import (
    AppearanceSpan,
    PersonContextSegment,
    build_person_context_segments,
)

VIDEO_EXTENSIONS = {".avi", ".m4v", ".mkv", ".mov", ".mp4", ".webm"}
IMAGE_EXTENSIONS = {".avif", ".jpeg", ".jpg", ".png", ".webp"}
UPLOAD_ROOT = Path("data/uploads")
DEFAULT_FOUR_VIEW_PROMPT = (
    "请根据我提供的参考帧，生成一张动漫角色设定图 / 角色多视图原图。"
    "输出必须是一张干净的横向单图，不要拆成多张文件。画面参考动画角色设定表："
    "左侧主体区依次放正面全身、侧面全身、背面全身、45 度全身或半身姿态，"
    "四个主体高度接近、比例一致、脚底对齐。右侧增加两列细节区：第一列放 45 度脸部特写"
    "和轻微微表情变化，第二列放服装/发型/配饰或材质细节特写。所有视图必须是同一个角色，"
    "脸型、眼睛、发型、发色、服装、配饰、主色调、"
    "年龄感、气质和画风都要保持一致。优先参考图片中被框选或最清晰的人物，"
    "不要把背景、路人或其他角色混进来。全身比例需要做动漫角色设定稿的理想化美化："
    "头身比更修长，腰线略高，腿部明显修长，腿长占比更漂亮，肩腰腿比例干净利落，"
    "站姿挺拔自然，整体接近动漫中的完美身材。这种美化只允许优化身材比例和姿态，"
    "不允许改脸、改发型、改发色、改服装结构、改角色身份，也不要把角色改成另一个人。"
    "画风要求为动漫角色设定稿、清晰线稿、轮廓明确、赛璐璐平涂、光照中性、白色或浅灰纯色背景。"
    "禁止出现文字、标签、说明、签名、水印、UI 元素、Logo、对白气泡、多个角色、额外肢体、"
    "重复头部、随机道具、换装、发型或发色漂移、不同画风混杂。"
)


def _result_store(config=None) -> ResultStore:
    """按配置创建结果库入口。"""
    current_config = config or load_config()
    return ResultStore(current_config.database.path, url=current_config.database.url)


class AnalyzeRequest(BaseModel):
    """视频分析请求体。"""

    video_path: str  # 视频文件路径
    preset: str | None = "fast"  # 预设配置名称
    use_cache: bool = True  # 是否使用缓存
    expected_people_count: int | None = Field(default=None, ge=1)  # 预设人物数量，None 表示自动
    display_title: str | None = None  # 展示用视频标题
    series_name: str | None = None  # 作品/系列名称
    original_filename: str | None = None  # 原始文件名
    source_path: str | None = None  # 原始源媒体路径
    source_directory: str | None = None  # 原始源媒体所在目录
    hardware_profile: str | None = None  # auto/cpu/apple/nvidia/intel
    allow_cpu_fallback: bool | None = None  # GPU/CoreML 失败时是否允许降级 CPU
    config_path: str | None = None  # 单次分析使用的 TOML 配置文件路径，留空使用 configs/default.toml


class AnalyzeBatchRequest(BaseModel):
    """批量视频分析请求体。"""

    video_paths: list[str] | str  # 视频文件路径列表，或用分号分隔的路径字符串
    preset: str | None = "fast"  # 预设配置名称
    use_cache: bool = True  # 是否使用缓存
    expected_people_count: int | None = Field(default=None, ge=1)  # 预设人物数量，None 表示自动
    display_title: str | None = None  # 单视频展示标题
    series_name: str | None = None  # 批量视频所属作品/系列
    original_filename: str | None = None  # 单视频原始文件名
    source_path: str | None = None  # 单视频原始源媒体路径
    source_directory: str | None = None  # 单视频原始源媒体所在目录
    hardware_profile: str | None = None  # auto/cpu/apple/nvidia/intel
    allow_cpu_fallback: bool | None = None  # GPU/CoreML 失败时是否允许降级 CPU
    config_path: str | None = None  # 批量分析使用的 TOML 配置文件路径，留空使用 configs/default.toml


class AnalyzeJobItemStatus(BaseModel):
    """批量分析任务中的单个视频状态。"""

    video_path: str
    status: str
    stage: str
    progress: float
    message: str
    video_id: int | None = None
    timeline_path: str | None = None
    error: str | None = None


class AnalyzeJobStatus(BaseModel):
    """视频分析任务状态。"""

    job_id: str
    status: str
    stage: str
    progress: float
    message: str
    video_id: int | None = None
    timeline_path: str | None = None
    error: str | None = None
    video_path: str | None = None
    video_paths: list[str] = Field(default_factory=list)
    total: int = 1
    completed: int = 0
    failed: int = 0
    current_index: int | None = None
    items: list[AnalyzeJobItemStatus] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None


class ImportTimelineRequest(BaseModel):
    """导入 timeline 请求体。"""

    timeline_path: str  # timeline.json 文件路径
    display_title: str | None = None  # 展示标题
    series_name: str | None = None  # 作品/系列
    original_filename: str | None = None  # 原始文件名
    source_path: str | None = None  # 原始源媒体路径
    source_directory: str | None = None  # 原始源媒体所在目录


class UpdateVideoRequest(BaseModel):
    """更新视频作品信息请求体。"""

    title: str | None = None
    series_name: str | None = None
    original_filename: str | None = None
    source_path: str | None = None
    source_directory: str | None = None


class RenamePersonRequest(BaseModel):
    """重命名人物请求体。"""

    label: str  # 新标签


class PersonVisibilityRequest(BaseModel):
    """人物默认视图可见性请求体。"""

    hidden: bool = False


class MergePeopleRequest(BaseModel):
    """合并人物请求体。"""

    source_person_id: int  # 源人物 ID
    target_person_id: int  # 目标人物 ID


class SplitTracksRequest(BaseModel):
    """拆分轨迹请求体。"""

    source_person_id: int  # 源人物 ID
    track_ids: list[int]  # 要拆分的轨迹 ID 列表
    label: str | None = None  # 新人物标签，None 则自动生成


class AssignTracksRequest(BaseModel):
    """批量归类轨迹请求体。"""

    track_ids: list[int]  # 要归类的轨迹 ID 列表
    target_person_id: int  # 目标人物 ID


class DeleteTracksRequest(BaseModel):
    """批量删除轨迹请求体。"""

    track_ids: list[int]  # 要删除的轨迹 ID 列表


class GlobalObservationReviewRequest(BaseModel):
    """全局观测审核请求体。"""

    video_path: str  # 视频文件路径
    local_person_id: int  # 视频内人物 ID


class GlobalPersonLinkRequest(BaseModel):
    """本地人物关联人物档案请求体。"""

    global_person_id: str


class GlobalPersonCreateRequest(BaseModel):
    """从本地人物新建人物档案请求体。"""

    label: str | None = None


class ManualGlobalPersonCreateRequest(BaseModel):
    """手动新建空白人物档案请求体。"""

    label: str = Field(min_length=1)

    @field_validator("label")
    @classmethod
    def normalize_label(cls, value: str) -> str:
        """清理用户输入，拒绝空白名称。"""
        label = value.strip()
        if not label:
            raise ValueError("label must not be blank")
        return label


class GlobalPersonRenameRequest(BaseModel):
    """重命名人物档案请求体。"""

    label: str = Field(min_length=1)

    @field_validator("label")
    @classmethod
    def normalize_label(cls, value: str) -> str:
        """清理用户输入，拒绝空白名称。"""
        label = value.strip()
        if not label:
            raise ValueError("label must not be blank")
        return label


class GlobalPeopleMergeRequest(BaseModel):
    """跨视频人物档案合并请求体。"""

    source_global_person_id: str


class FourViewAssetMoveRequest(BaseModel):
    """四视图资产迁移请求体。"""

    target_global_person_id: str


class FourViewReferenceRequest(BaseModel):
    """四视图生成使用的一张参考素材。"""

    video_id: int | None = None
    frame_index: int | None = Field(default=None, ge=0)
    timestamp: float | None = Field(default=None, ge=0)
    face_path: str | None = None
    label: str | None = None


class FourViewGenerateRequest(BaseModel):
    """基于参考素材生成四视图原图的请求体。"""

    label: str | None = None
    prompt: str | None = None
    references: list[FourViewReferenceRequest] = Field(min_length=1, max_length=12)


_ANALYSIS_JOBS: dict[str, AnalyzeJobStatus] = {}
_ANALYSIS_JOBS_LOCK = threading.Lock()
_ANALYSIS_REQUESTS: dict[str, AnalyzeBatchRequest] = {}
_ANALYSIS_CANCEL_EVENTS: dict[str, threading.Event] = {}
_ANALYSIS_QUEUE: queue.Queue[str] = queue.Queue()
_ANALYSIS_WORKER_STARTED = False
_ANALYSIS_WORKER_LOCK = threading.Lock()


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用。"""
    config = load_config()
    store = _result_store(config)
    app = FastAPI(title="FaceTimeMarker API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        """健康检查接口。"""
        return {"status": "ok"}

    @app.get("/api/config")
    def get_config():
        """返回当前应用配置。"""
        return config.model_dump(mode="json", by_alias=True)

    @app.get("/api/presets")
    def presets():
        """返回可用预设名称列表。"""
        return list(PRESET_NAMES)

    @app.get("/api/hardware")
    def hardware():
        """返回当前机器硬件和 ONNX Runtime provider 摘要。"""
        return hardware_summary()

    @app.get("/api/videos")
    def videos(include_deleted: bool = False, only_deleted: bool = False):
        """列出所有视频。"""
        return store.list_videos(include_deleted=include_deleted, only_deleted=only_deleted)

    @app.get("/api/videos/{video_id}")
    def video(video_id: int):
        """获取单个视频详情。"""
        return _video_detail(store, video_id)

    @app.patch("/api/videos/{video_id}")
    def update_video(video_id: int, request: UpdateVideoRequest):
        """更新视频展示标题和作品系列。"""
        try:
            return store.update_video_metadata(
                video_id,
                title=request.title,
                series_name=request.series_name,
                original_filename=request.original_filename,
                source_path=request.source_path,
                source_directory=request.source_directory,
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.delete("/api/videos/{video_id}")
    def trash_video(video_id: int):
        """把视频移入回收站。"""
        try:
            return store.move_video_to_trash(video_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/videos/{video_id}/restore")
    def restore_video(video_id: int):
        """从回收站恢复视频。"""
        try:
            return store.restore_video(video_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.delete("/api/videos/{video_id}/purge")
    def purge_video(video_id: int):
        """彻底删除视频在库中的分析数据。"""
        try:
            store.purge_video(video_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"status": "deleted"}

    @app.get("/api/videos/{video_id}/people")
    def people(video_id: int):
        """获取视频下的人物列表。"""
        return store.list_people(video_id)

    @app.get("/api/videos/{video_id}/segments")
    def segments(video_id: int, person_id: int | None = None):
        """获取视频的时间轴片段，可按人物过滤。"""
        return store.list_segments(video_id, person_id)

    @app.get("/api/videos/{video_id}/context-segments")
    def context_segments(
        video_id: int,
        person_id: int | None = None,
        padding_seconds: float = Query(12.0, ge=0),
        max_gap_seconds: float = Query(45.0, ge=0),
        min_presence_ratio: float = Query(0.08, ge=0, le=1),
        min_source_segments: int = Query(2, ge=1),
    ):
        """按人物出现频率生成更适合整段观看的上下文片段。"""
        video_item = store.get_video(video_id)
        if video_item is None:
            raise HTTPException(status_code=404, detail="Video not found")
        segment_rows = store.list_segments(video_id, person_id)
        labels = {person["person_id"]: person["label"] for person in store.list_people(video_id)}
        context_items: list[dict] = []
        for local_person_id, rows in _group_segment_rows_by_person(segment_rows).items():
            spans = [_appearance_span_from_segment_row(row) for row in rows]
            context_items.extend(
                _context_segment_to_dict(segment, labels.get(local_person_id))
                for segment in build_person_context_segments(
                    spans,
                    video_duration=float(video_item["duration_seconds"]),
                    padding_seconds=padding_seconds,
                    max_gap_seconds=max_gap_seconds,
                    min_presence_ratio=min_presence_ratio,
                    min_source_segments=min_source_segments,
                )
            )
        return sorted(context_items, key=lambda item: (item["person_id"], item["start"]))

    @app.get("/api/videos/{video_id}/tracks")
    def tracks(video_id: int, person_id: int | None = None):
        """获取视频的人脸轨迹，可按人物过滤。"""
        return store.list_tracks(video_id, person_id)

    @app.get("/api/videos/{video_id}/track-detections")
    def track_detections(
        video_id: int,
        person_id: int | None = None,
        track_id: int | None = None,
        start: float | None = Query(None, ge=0),
        end: float | None = Query(None, ge=0),
        limit: int = Query(0, ge=0),
    ):
        """获取视频的逐帧人脸框，可用于播放叠加和参考图导出。"""
        max_rows = config.frame_boxes.max_api_rows
        effective_limit = limit if limit > 0 else max_rows
        return store.list_track_detections(
            video_id,
            person_id=person_id,
            track_id=track_id,
            start=start,
            end=end,
            limit=min(effective_limit, max_rows),
        )

    @app.get("/api/videos/{video_id}/face-crops")
    def face_crops(video_id: int, person_id: int | None = None):
        """获取视频的人脸截图，可按人物过滤。"""
        return store.list_face_crops(video_id, person_id)

    @app.get("/api/videos/{video_id}/frame")
    def video_frame(
        video_id: int,
        frame_index: int | None = Query(None, ge=0),
        timestamp: float | None = Query(None, ge=0),
    ):
        """按帧号或时间戳抽取视频完整画面，用于人物参考素材预览。"""
        item = store.get_video(video_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Video not found")
        return _extract_video_frame_response(item, frame_index, timestamp)

    @app.get("/api/global-people")
    def global_people(
        include_hidden: bool = False,
        include_deleted: bool = False,
        only_deleted: bool = False,
    ):
        """列出所有跨视频全局人物。"""
        return store.list_global_people(
            include_hidden=include_hidden,
            include_deleted=include_deleted,
            only_deleted=only_deleted,
        )

    @app.post("/api/global-people")
    def create_manual_global_person(request: ManualGlobalPersonCreateRequest):
        """手动创建一个空白人物档案，不依赖视频识别结果。"""
        try:
            global_person_id = store.create_manual_global_person(request.label)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "global_person_id": global_person_id,
            "global_people": store.list_global_people(include_hidden=True),
        }

    @app.delete("/api/global-people/{global_person_id}")
    def delete_global_person(global_person_id: str):
        """把一个人物档案移入回收站。"""
        try:
            store.delete_global_person(global_person_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {
            "global_people": store.list_global_people(include_hidden=True),
            "deleted_global_people": store.list_global_people(include_hidden=True, only_deleted=True),
        }

    @app.post("/api/global-people/{global_person_id}/restore")
    def restore_global_person(global_person_id: str):
        """从人物档案回收站恢复档案。"""
        try:
            store.restore_global_person(global_person_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {
            "global_people": store.list_global_people(include_hidden=True),
            "deleted_global_people": store.list_global_people(include_hidden=True, only_deleted=True),
        }

    @app.delete("/api/global-people/{global_person_id}/purge")
    def purge_global_person(global_person_id: str):
        """彻底删除人物档案，并解除本地人物关联。"""
        try:
            store.purge_global_person(global_person_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {
            "global_people": store.list_global_people(include_hidden=True),
            "deleted_global_people": store.list_global_people(include_hidden=True, only_deleted=True),
        }

    @app.patch("/api/global-people/{global_person_id}")
    def rename_global_person(global_person_id: str, request: GlobalPersonRenameRequest):
        """重命名人物档案的全局展示名称。"""
        try:
            store.rename_global_person(global_person_id, request.label)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "global_person_id": global_person_id,
            "global_people": store.list_global_people(include_hidden=True),
        }

    @app.post("/api/global-people/{target_global_person_id}/merge")
    def merge_global_people(target_global_person_id: str, request: GlobalPeopleMergeRequest):
        """把源人物档案合并进目标人物档案，保留目标 ID。"""
        try:
            store.merge_global_people(
                request.source_global_person_id,
                target_global_person_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "global_people": store.list_global_people(include_hidden=True),
            "observations": store.list_global_observations(target_global_person_id, include_hidden=True),
            "four_view_assets": store.list_four_view_assets(target_global_person_id),
        }

    @app.get("/api/global-person-actions")
    def global_person_actions(global_person_id: str | None = None, limit: int = Query(100, ge=1, le=200)):
        """读取人物档案操作历史。"""
        return store.list_global_person_actions(global_person_id, limit=limit)

    @app.get("/api/global-people/{global_person_id}/observations")
    def global_observations(global_person_id: str, include_hidden: bool = False):
        """获取指定全局人物的观测记录。"""
        return store.list_global_observations(global_person_id, include_hidden=include_hidden)

    @app.get("/api/global-people/{global_person_id}/four-view-assets")
    def four_view_assets(global_person_id: str):
        """读取某个人物档案下已上传或生成的四视图原图资产。"""
        try:
            return store.list_four_view_assets(global_person_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/global-people/{global_person_id}/four-view-assets")
    def upload_four_view_asset(
        global_person_id: str,
        file: Annotated[UploadFile, File(...)],
        label: Annotated[str | None, Form()] = None,
    ):
        """上传一张未切分的四视图原图，挂到指定人物档案。"""
        try:
            store.list_four_view_assets(global_person_id)
            saved_path = _save_profile_asset_upload(config, file)
            return store.add_four_view_asset(
                global_person_id,
                image_path=str(saved_path),
                label=label,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/global-people/{global_person_id}/four-view-assets/generate")
    def generate_four_view_asset(global_person_id: str, request: FourViewGenerateRequest):
        """基于选中的参考素材调用图像生成服务，生成一张未切分四视图原图。"""
        try:
            store.list_four_view_assets(global_person_id)
            generated_path = _generate_four_view_image(config, store, global_person_id, request)
            return store.add_four_view_asset(
                global_person_id,
                image_path=str(generated_path),
                label=request.label,
                reference_count=len(request.references),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/global-people/{source_global_person_id}/four-view-assets/move")
    def move_four_view_assets(source_global_person_id: str, request: FourViewAssetMoveRequest):
        """把当前档案的四视图资产迁移到另一个人物档案。"""
        try:
            result = store.move_four_view_assets(
                source_global_person_id,
                request.target_global_person_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            **result,
            "global_people": store.list_global_people(include_hidden=True),
        }

    @app.delete("/api/global-people/{global_person_id}/four-view-assets/{asset_id}")
    def delete_four_view_asset(global_person_id: str, asset_id: int):
        """删除人物档案下的一张四视图原图资产。"""
        try:
            deleted = store.delete_four_view_asset(global_person_id, asset_id)
            _delete_profile_asset_file(config, deleted.get("image_path"))
            return {
                "deleted_asset": deleted,
                "four_view_assets": store.list_four_view_assets(global_person_id),
                "global_people": store.list_global_people(include_hidden=True),
            }
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/search/people")
    def search_people(q: str = "", limit: int = Query(50, ge=1, le=200)):
        """按备注、全局人物 ID、视频标题和路径搜索人物。"""
        return store.search_people(q, limit=limit)

    @app.post("/api/search/faces")
    def search_faces(
        file: Annotated[UploadFile, File(...)],
        limit: int = Query(10, ge=1, le=50),
        min_similarity: float | None = Query(None, ge=-1.0, le=1.0),
    ):
        """上传一张人脸图，在全局人物库中按 embedding 相似度搜索。"""
        return _search_global_people_by_face(config, file, limit, min_similarity)

    @app.post("/api/global-people/{global_person_id}/confirm")
    def confirm_global_observation(
        global_person_id: str,
        request: GlobalObservationReviewRequest,
    ):
        """确认某个观测属于指定全局人物。"""
        identity_store = _identity_store(config)
        try:
            identity_store.confirm_observation(
                global_person_id,
                request.video_path,
                request.local_person_id,
            )
            identity_store.save()
            store.confirm_global_observation(
                global_person_id,
                request.video_path,
                request.local_person_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "global_people": store.list_global_people(),
            "observations": store.list_global_observations(global_person_id),
        }

    @app.post("/api/global-people/{global_person_id}/reject")
    def reject_global_observation(
        global_person_id: str,
        request: GlobalObservationReviewRequest,
    ):
        """拒绝某个观测与原全局人物的关联，并将其拆分为新全局人物。"""
        identity_store = _identity_store(config)
        try:
            new_global_person_id = identity_store.reject_observation(
                global_person_id,
                request.video_path,
                request.local_person_id,
            )
            identity_store.save()
            store.reject_global_observation(
                global_person_id,
                request.video_path,
                request.local_person_id,
                new_global_person_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "new_global_person_id": new_global_person_id,
            "global_people": store.list_global_people(),
            "observations": store.list_global_observations(new_global_person_id),
        }

    @app.post("/api/videos/{video_id}/people/{person_id}/global-link")
    def link_global_person(video_id: int, person_id: int, request: GlobalPersonLinkRequest):
        """将本视频人物关联到指定人物档案。"""
        try:
            store.link_person_to_global(video_id, person_id, request.global_person_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _video_detail(store, video_id)

    @app.post("/api/videos/{video_id}/people/{person_id}/global-person")
    def create_global_person(
        video_id: int,
        person_id: int,
        request: GlobalPersonCreateRequest,
    ):
        """从本视频人物直接新建人物档案并关联。"""
        try:
            global_person_id = store.create_global_person_from_local(
                video_id,
                person_id,
                request.label,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        item = _video_detail(store, video_id)
        item["global_person_id"] = global_person_id
        return item

    @app.patch("/api/videos/{video_id}/people/{person_id}")
    def rename_person(video_id: int, person_id: int, request: RenamePersonRequest):
        """重命名视频中的人物。"""
        try:
            store.rename_person(video_id, person_id, request.label)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _video_detail(store, video_id)

    @app.patch("/api/videos/{video_id}/people/{person_id}/visibility")
    def set_person_visibility(
        video_id: int,
        person_id: int,
        request: PersonVisibilityRequest,
    ):
        """隐藏或恢复显示视频中的人物，默认视图会过滤隐藏人物。"""
        try:
            store.set_person_hidden(video_id, person_id, request.hidden)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _video_detail(store, video_id)

    @app.post("/api/videos/{video_id}/people/merge")
    def merge_people(video_id: int, request: MergePeopleRequest):
        """合并视频中的两个人物。"""
        try:
            store.merge_people(video_id, request.source_person_id, request.target_person_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _video_detail(store, video_id)

    @app.post("/api/videos/{video_id}/people/split")
    def split_people(video_id: int, request: SplitTracksRequest):
        """将指定轨迹从源人物拆分出来，形成新人物。"""
        try:
            new_person_id = store.split_tracks_to_person(
                video_id,
                source_person_id=request.source_person_id,
                track_ids=request.track_ids,
                label=request.label,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        item = _video_detail(store, video_id)
        item["new_person_id"] = new_person_id
        return item

    @app.post("/api/videos/{video_id}/tracks/assign")
    def assign_tracks(video_id: int, request: AssignTracksRequest):
        """将一批轨迹统一归类到目标人物。"""
        try:
            store.assign_tracks_to_person(video_id, request.track_ids, request.target_person_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _video_detail(store, video_id)

    @app.delete("/api/videos/{video_id}/tracks")
    def delete_tracks(video_id: int, request: DeleteTracksRequest):
        """删除一批误检轨迹。"""
        try:
            store.delete_tracks(video_id, request.track_ids)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _video_detail(store, video_id)

    @app.delete("/api/videos/{video_id}/people/{person_id}")
    def delete_person(video_id: int, person_id: int):
        """删除视频中的人物。"""
        try:
            store.delete_person(video_id, person_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _video_detail(store, video_id)

    @app.post("/api/analyze")
    def analyze(request: AnalyzeRequest):
        """分析视频并将结果导入数据库。"""
        video_path = Path(request.video_path)
        if not video_path.exists():
            raise HTTPException(status_code=404, detail="Video path not found")
        if request.preset is not None and request.preset not in PRESET_NAMES:
            raise HTTPException(status_code=400, detail="Unsupported preset")
        config_path = _request_config_path(request)
        if config_path is not None and not config_path.exists():
            raise HTTPException(status_code=404, detail=f"Config file not found: {config_path}")
        next_config = _analysis_config(request)
        analysis_path, source_metadata = _prepare_analysis_media(video_path, request, next_config)
        timeline_path = FaceVideoPipeline(next_config, progress_factory=None).run(
            analysis_path,
            preset=request.preset,
            use_cache=request.use_cache,
            output_name=source_metadata.get("original_filename"),
        )
        video_id = _result_store(next_config).import_timeline(
            timeline_path,
            display_title=request.display_title,
            series_name=request.series_name,
            **source_metadata,
        )
        return {"video_id": video_id, "timeline_path": str(timeline_path)}

    @app.post("/api/analyze-jobs")
    def start_analyze_job(request: AnalyzeRequest) -> AnalyzeJobStatus:
        """启动后台分析任务并立即返回任务 ID。"""
        return _enqueue_analyze_batch(
            AnalyzeBatchRequest(
                video_paths=[request.video_path],
                preset=request.preset,
                use_cache=request.use_cache,
                expected_people_count=request.expected_people_count,
                display_title=request.display_title,
                series_name=request.series_name,
                original_filename=request.original_filename,
                source_path=request.source_path,
                source_directory=request.source_directory,
                hardware_profile=request.hardware_profile,
                allow_cpu_fallback=request.allow_cpu_fallback,
                config_path=request.config_path,
            )
        )

    @app.post("/api/analyze-batch-jobs")
    def start_analyze_batch_job(request: AnalyzeBatchRequest) -> AnalyzeJobStatus:
        """启动本地视频路径批量分析队列。"""
        return _enqueue_analyze_batch(request)

    @app.get("/api/analyze-jobs")
    def list_analyze_jobs(limit: Annotated[int, Query(ge=1, le=50)] = 10) -> list[AnalyzeJobStatus]:
        """读取最近的分析任务，供刷新页面后恢复任务进度。"""
        jobs = _result_store().list_analyze_jobs(limit=limit)
        return [AnalyzeJobStatus.model_validate(job) for job in jobs]

    @app.get("/api/analyze-jobs/{job_id}")
    def get_analyze_job(job_id: str) -> AnalyzeJobStatus:
        """读取后台分析任务状态。"""
        job = _get_analysis_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Analyze job not found")
        return job

    @app.post("/api/analyze-jobs/{job_id}/cancel")
    def cancel_analyze_job(job_id: str) -> AnalyzeJobStatus:
        """请求终止后台分析任务。"""
        job = _cancel_analysis_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Analyze job not found")
        return job

    @app.post("/api/upload-video")
    def upload_video(file: Annotated[UploadFile, File(...)]):
        """接收上传的视频文件并保存到本地目录。"""
        original_name = Path(file.filename or "").name
        suffix = Path(original_name).suffix.lower()
        # 检查文件后缀是否在允许的视频格式列表中
        if suffix not in VIDEO_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Unsupported video file type")

        upload_dir = UPLOAD_ROOT / datetime.now(UTC).strftime("%Y%m%d")
        upload_dir.mkdir(parents=True, exist_ok=True)
        saved_path = _upload_target_path(config, upload_dir, original_name, suffix)
        try:
            with saved_path.open("wb") as target:
                shutil.copyfileobj(file.file, target)
        finally:
            file.file.close()

        return {
            "video_path": str(saved_path),
            "filename": original_name,
            "source_path": str(saved_path),
            "source_directory": str(saved_path.parent),
            "size": saved_path.stat().st_size,
        }

    @app.post("/api/import-timeline")
    def import_timeline(request: ImportTimelineRequest):
        """将已有的 timeline.json 导入数据库。"""
        timeline_path = Path(request.timeline_path)
        if not timeline_path.exists():
            raise HTTPException(status_code=404, detail="Timeline path not found")
        video_id = store.import_timeline(
            timeline_path,
            display_title=request.display_title,
            series_name=request.series_name,
            original_filename=request.original_filename,
            source_path=request.source_path,
            source_directory=request.source_directory,
        )
        return {"video_id": video_id}

    @app.get("/media")
    def media(path: str):
        """提供媒体文件访问。"""
        media_path = Path(path)
        if not media_path.exists() or not media_path.is_file():
            raise HTTPException(status_code=404, detail="Media not found")
        return FileResponse(media_path)

    return app


def _video_detail(store: ResultStore, video_id: int):
    """组装视频详情，包含人物、片段、轨迹和截图。"""
    item = store.get_video(video_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Video not found")
    item["people"] = store.list_people(video_id)
    item["segments"] = store.list_segments(video_id)
    item["tracks"] = store.list_tracks(video_id)
    item["face_crops"] = store.list_face_crops(video_id)
    return item


def _extract_video_frame_response(
    video_item: dict,
    frame_index: int | None,
    timestamp: float | None,
) -> Response:
    """从视频文件中抽取一帧并编码为 JPEG 响应。"""
    content = _extract_video_frame_bytes(video_item, frame_index, timestamp)
    return Response(
        content=content,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=3600"},
    )


def _extract_video_frame_bytes(
    video_item: dict,
    frame_index: int | None,
    timestamp: float | None,
) -> bytes:
    """从视频文件中抽取一帧并编码为 JPEG 字节。"""
    if frame_index is None and timestamp is None:
        raise HTTPException(status_code=400, detail="frame_index or timestamp is required")

    capture = None
    for candidate in _video_media_candidates(video_item):
        if not candidate.exists() or not candidate.is_file():
            continue
        capture = cv2.VideoCapture(str(candidate))
        if capture.isOpened():
            break
        capture.release()
        capture = None
    if capture is None:
        raise HTTPException(status_code=404, detail="Video media not found")

    try:
        if frame_index is not None:
            capture.set(cv2.CAP_PROP_POS_FRAMES, int(frame_index))
        else:
            capture.set(cv2.CAP_PROP_POS_MSEC, float(timestamp or 0.0) * 1000)
        ok, frame = capture.read()
        if not ok or frame is None:
            raise HTTPException(status_code=404, detail="Frame not found")
        encoded_ok, encoded = cv2.imencode(".jpg", frame)
        if not encoded_ok:
            raise HTTPException(status_code=500, detail="Frame encoding failed")
        return encoded.tobytes()
    finally:
        capture.release()


def _video_media_candidates(video_item: dict) -> list[Path]:
    """返回视频当前分析路径和源路径候选，保持顺序去重。"""
    candidates: list[Path] = []
    seen: set[str] = set()
    for key in ("path", "source_path"):
        raw = str(video_item.get(key) or "").strip()
        if not raw:
            continue
        path = Path(raw).expanduser()
        marker = str(path)
        if marker in seen:
            continue
        candidates.append(path)
        seen.add(marker)
    return candidates


def _prepare_analysis_media(video_path: Path, request: AnalyzeRequest, config) -> tuple[Path, dict]:
    """根据源媒体配置返回实际分析路径和需要写入数据库的源信息。"""
    source_path = _clean_optional_text(request.source_path) or str(video_path)
    source_directory = _clean_optional_text(request.source_directory) or str(Path(source_path).parent)
    original_filename = (
        _clean_optional_text(request.original_filename)
        or _clean_optional_text(request.display_title)
        or Path(source_path).name
    )
    analysis_path = video_path
    if config.source_media.copy_source_files and not _is_under_upload_root(video_path):
        upload_dir = UPLOAD_ROOT / datetime.now(UTC).strftime("%Y%m%d")
        upload_dir.mkdir(parents=True, exist_ok=True)
        copied_path = _unique_path(upload_dir / _safe_filename(video_path.name, video_path.suffix))
        shutil.copy2(video_path, copied_path)
        analysis_path = copied_path
    return analysis_path, {
        "original_filename": original_filename,
        "source_path": source_path,
        "source_directory": source_directory,
    }


def _upload_target_path(config, upload_dir: Path, original_name: str, suffix: str) -> Path:
    """按配置生成浏览器上传文件的保存路径。"""
    naming = config.source_media.upload_file_naming.strip().lower()
    if naming == "hash":
        return _unique_path(upload_dir / f"{uuid4().hex}{suffix}")
    return _unique_path(upload_dir / _safe_filename(original_name, suffix))


def _save_profile_asset_upload(config, file: UploadFile) -> Path:
    """保存人物档案资产图片，并返回本地文件路径。"""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in IMAGE_EXTENSIONS:
        file.file.close()
        raise ValueError("Unsupported image file")
    upload_dir = _profile_asset_dir(config, "manual")
    upload_dir.mkdir(parents=True, exist_ok=True)
    saved_path = _unique_path(upload_dir / _safe_filename(file.filename or "four-view", suffix))
    with saved_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    file.file.close()
    return saved_path


def _profile_asset_dir(config, category: str) -> Path:
    """返回人物档案资产目录，长期资产放在输出根目录而不是上传临时目录。"""
    safe_category = _safe_filename(category or "assets", "")
    return config.output.root / "profile-assets" / safe_category / datetime.now(UTC).strftime("%Y%m%d")


def _generate_four_view_image(
    config,
    store: ResultStore,
    global_person_id: str,
    request: FourViewGenerateRequest,
) -> Path:
    """调用图像生成服务生成四视图原图，并保存到本地。"""
    if not config.large_model.enabled:
        raise ValueError("large model is disabled in configs/ai.toml")
    if not config.image_generation.enabled:
        raise ValueError("image generation is disabled in configs/ai.toml")
    if not config.large_model.api_key.strip():
        raise ValueError("large model API key is empty")

    references = _resolve_four_view_reference_images(store, request.references)
    prompt = _clean_optional_text(request.prompt) or config.image_generation.prompt_template.strip() or DEFAULT_FOUR_VIEW_PROMPT
    image_bytes = _call_litellm_image_edit(config, prompt, references)
    return _save_generated_four_view_image(
        config,
        global_person_id,
        image_bytes,
        config.image_generation.output_format,
        config.image_generation.output_compression,
        _four_view_asset_base_name(store, global_person_id, request),
    )


def _resolve_four_view_reference_images(
    store: ResultStore,
    references: list[FourViewReferenceRequest],
) -> list[tuple[str, bytes]]:
    """把前端选择的参考素材解析成可上传给图像生成接口的图片字节。"""
    images: list[tuple[str, bytes]] = []
    for index, reference in enumerate(references[:12], start=1):
        content: bytes | None = None
        if reference.video_id is not None:
            video_item = store.get_video(reference.video_id)
            if video_item is not None and (
                reference.frame_index is not None or reference.timestamp is not None
            ):
                content = _extract_video_frame_bytes(
                    video_item,
                    reference.frame_index,
                    reference.timestamp,
                )
        if content is None and reference.face_path:
            path = Path(reference.face_path).expanduser()
            if path.exists() and path.is_file():
                content = path.read_bytes()
        if content:
            images.append((f"reference-{index}.jpg", content))
    if not images:
        raise ValueError("no usable reference images")
    return images


def _call_litellm_image_edit(
    config,
    prompt: str,
    references: list[tuple[str, bytes]],
) -> bytes:
    """通过 LiteLLM image_edit 调用图像生成服务并返回图片字节。"""
    model = (
        config.image_generation.model.strip()
        or config.large_model.model.strip()
        or "gpt-image-2"
    )
    provider = config.large_model.provider.strip()
    if provider and provider not in {"openai", "openai_compatible", "custom"} and "/" not in model:
        model = f"{provider}/{model}"

    temp_paths: list[Path] = []
    handles = []
    try:
        for filename, content in references:
            suffix = Path(filename).suffix or ".jpg"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as buffer:
                buffer.write(content)
                temp_paths.append(Path(buffer.name))
        handles = [path.open("rb") for path in temp_paths]
        kwargs = {
            "model": model,
            "image": handles if len(handles) > 1 else handles[0],
            "prompt": prompt,
            "api_key": config.large_model.api_key,
            "api_base": config.large_model.base_url,
            "n": 1,
        }
        if config.image_generation.size and config.image_generation.size != "auto":
            kwargs["size"] = config.image_generation.size
        if config.image_generation.quality and config.image_generation.quality != "auto":
            kwargs["quality"] = config.image_generation.quality
        output_format = _normalize_generated_image_format(config.image_generation.output_format)
        if output_format:
            kwargs["output_format"] = output_format
        if output_format in {"jpeg", "webp"} and config.image_generation.output_compression is not None:
            kwargs["output_compression"] = config.image_generation.output_compression
        if config.image_generation.background and config.image_generation.background != "auto":
            kwargs["background"] = config.image_generation.background
        if config.image_generation.moderation and config.image_generation.moderation != "auto":
            kwargs["moderation"] = config.image_generation.moderation
        if config.image_generation.input_fidelity and config.image_generation.input_fidelity != "auto":
            kwargs["input_fidelity"] = config.image_generation.input_fidelity

        response = litellm.image_edit(**kwargs)
    except Exception as exc:
        raise ValueError("image generation failed") from exc
    finally:
        for handle in handles:
            handle.close()
        for path in temp_paths:
            path.unlink(missing_ok=True)

    data = getattr(response, "data", None)
    item = data[0] if data else None
    encoded_image = None
    if isinstance(item, dict):
        encoded_image = item.get("b64_json")
    else:
        encoded_image = getattr(item, "b64_json", None)
    if not encoded_image:
        raise ValueError("image generation response did not include b64_json")
    return base64.b64decode(encoded_image)


def _save_generated_four_view_image(
    config,
    global_person_id: str,
    content: bytes,
    output_format: str,
    output_compression: int | None,
    base_name: str | None,
) -> Path:
    """保存生成后的四视图原图。"""
    content, saved_format = _prepare_generated_image_bytes(content, output_format, output_compression)
    suffix = _generated_image_suffix(saved_format)
    asset_dir = _profile_asset_dir(config, "generated")
    asset_dir.mkdir(parents=True, exist_ok=True)
    name = _four_view_asset_filename(base_name or global_person_id, suffix)
    saved_path = _unique_path(asset_dir / name)
    saved_path.write_bytes(content)
    return saved_path


def _four_view_asset_filename(base_name: str, suffix: str) -> str:
    """生成四视图资产文件名，避免重复追加“四视图”。"""
    clean_base = base_name.strip() or "four-view"
    label = clean_base if "四视图" in clean_base else f"{clean_base}-四视图"
    return _safe_filename(f"{label}{suffix}", suffix)


def _four_view_asset_base_name(
    store: ResultStore,
    global_person_id: str,
    request: FourViewGenerateRequest,
) -> str:
    """根据参考素材生成可读文件名，优先使用来源视频文件名。"""
    video_names: list[str] = []
    for reference in request.references:
        if reference.video_id is None:
            continue
        video = store.get_video(reference.video_id)
        if video is None:
            continue
        name = _first_non_empty_text(
            video.get("original_filename"),
            video.get("title"),
            Path(str(video.get("source_path") or "")).name,
            Path(str(video.get("path") or "")).name,
        )
        if name:
            video_names.append(Path(name).stem)
    source_name = video_names[0] if video_names else None
    person_name = _clean_optional_text(request.label) or global_person_id
    if source_name:
        return f"{source_name}-{person_name}"
    return person_name


def _prepare_generated_image_bytes(
    content: bytes,
    output_format: str | None,
    output_compression: int | None,
) -> tuple[bytes, str]:
    """按配置准备生成图；兼容中转平台忽略 output_format 的情况。"""
    desired_format = _normalize_generated_image_format(output_format)
    effective_compression = output_compression if desired_format in {"jpeg", "webp"} else None
    detected_format = _detect_image_format(content)
    if detected_format == desired_format and effective_compression is None:
        return content, desired_format

    converted = _encode_generated_image(content, desired_format, effective_compression)
    if converted is not None:
        return converted, desired_format
    return content, detected_format or desired_format


def _normalize_generated_image_format(output_format: str | None) -> str:
    """归一化 OpenAI GPT Image 支持的输出格式。"""
    value = (output_format or "webp").strip().lower().lstrip(".")
    if value == "jpg":
        value = "jpeg"
    return value if value in {"png", "jpeg", "webp"} else "webp"


def _generated_image_suffix(image_format: str) -> str:
    """返回生成图保存后缀。"""
    suffix = f".{_normalize_generated_image_format(image_format)}"
    return suffix if suffix in IMAGE_EXTENSIONS else ".png"


def _detect_image_format(content: bytes) -> str | None:
    """根据文件头判断真实图片格式。"""
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if content.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "webp"
    return None


def _encode_generated_image(
    content: bytes,
    output_format: str,
    output_compression: int | None,
) -> bytes | None:
    """本地兜底转码，避免兼容接口返回 PNG 但用户要求 WebP/JPEG。"""
    if output_format not in {"png", "jpeg", "webp"}:
        return None
    image = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    if image is None:
        return None

    extension = ".jpg" if output_format == "jpeg" else f".{output_format}"
    params: list[int] = []
    if output_format == "jpeg":
        params = [cv2.IMWRITE_JPEG_QUALITY, output_compression if output_compression is not None else 100]
    elif output_format == "webp":
        params = [cv2.IMWRITE_WEBP_QUALITY, output_compression if output_compression is not None else 100]

    success, encoded = cv2.imencode(extension, image, params)
    return encoded.tobytes() if success else None


def _delete_profile_asset_file(config, image_path: str | None) -> None:
    """删除项目档案资产文件，限制在受管理目录内避免误删外部路径。"""
    if not image_path:
        return
    path = Path(image_path).expanduser()
    try:
        resolved_path = path.resolve()
        allowed_roots = (
            (config.output.root / "profile-assets").resolve(),
            (UPLOAD_ROOT / "profile-assets").resolve(),
        )
        if not any(_is_relative_to(resolved_path, root) for root in allowed_roots):
            return
    except (OSError, ValueError):
        return
    if resolved_path.is_file():
        resolved_path.unlink(missing_ok=True)


def _first_non_empty_text(*values) -> str:
    """返回第一个非空字符串。"""
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _safe_filename(filename: str, fallback_suffix: str) -> str:
    """清理浏览器上传文件名，保留可读名称并避免路径穿透。"""
    name = Path(filename).name.strip()
    if not name:
        name = f"upload{fallback_suffix}"
    cleaned = "".join(
        char if char >= " " and char not in '<>:"/\\|?*' else "_"
        for char in name
    ).strip(" .")
    if not cleaned:
        cleaned = f"upload{fallback_suffix}"
    if not Path(cleaned).suffix and fallback_suffix:
        cleaned = f"{cleaned}{fallback_suffix}"
    return cleaned


def _unique_path(path: Path) -> Path:
    """如果目标路径已存在，则在文件名后追加可读数字后缀。"""
    if not path.exists():
        return path
    for index in range(2, 1000):
        candidate = path.with_name(f"{path.stem}-{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    return path.with_name(f"{path.stem}-{uuid4().hex[:8]}{path.suffix}")


def _is_relative_to(path: Path, root: Path) -> bool:
    """兼容旧 Python 写法的 relative_to 布尔判断。"""
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _is_under_upload_root(path: Path) -> bool:
    """判断路径是否已经位于上传目录，避免重复复制浏览器上传文件。"""
    try:
        path.resolve().relative_to(UPLOAD_ROOT.resolve())
        return True
    except ValueError:
        return False


def _clean_optional_text(value: str | None) -> str | None:
    """把空字符串规整为 None。"""
    if value is None:
        return None
    text = value.strip()
    return text or None


def _identity_store(config):
    """加载跨视频人物身份库。"""
    return IdentityStore.load(
        config.identity_store_path(),
        match_threshold=config.identity_store.match_threshold,
    )


def _analysis_config(request: AnalyzeRequest):
    """根据请求生成分析配置。"""
    config_path = _request_config_path(request)
    config = load_config(config_path) if config_path is not None else load_config()
    config = apply_preset(config, request.preset)
    if request.expected_people_count is not None:
        config.clustering.expected_people_count = request.expected_people_count
    if request.hardware_profile:
        config.face.execution_provider_profile = request.hardware_profile
    if request.allow_cpu_fallback is not None:
        config.face.allow_cpu_fallback = request.allow_cpu_fallback
    return config


def _request_config_path(request: AnalyzeRequest | AnalyzeBatchRequest) -> Path | None:
    """返回单次分析请求指定的配置路径。"""
    raw = request.config_path.strip() if request.config_path else ""
    if not raw:
        return None
    return Path(raw).expanduser()


def _search_global_people_by_face(
    config,
    file: UploadFile,
    limit: int,
    min_similarity: float | None = None,
) -> list[dict]:
    """提取上传图片的人脸 embedding，并在全局人物库里按相似度检索。"""
    image_bytes = file.file.read()
    file.file.close()
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="Unsupported image file")

    analyzer = InsightFaceAnalyzer(config.face)
    detections = analyzer.analyze(Frame(index=0, timestamp=0.0, image=image))
    detections = [detection for detection in detections if detection.embedding is not None]
    if not detections:
        raise HTTPException(status_code=400, detail="No face found in image")

    detection = max(
        detections,
        key=lambda item: _face_search_quality(item.bbox_xyxy, item.confidence),
    )
    embedding = np.asarray(detection.embedding, dtype=np.float32)
    norm = float(np.linalg.norm(embedding))
    if norm <= 0:
        raise HTTPException(status_code=400, detail="Invalid face embedding")
    embedding = embedding / norm

    threshold = (
        float(min_similarity)
        if min_similarity is not None
        else float(config.identity_store.match_threshold)
    )
    identity_store = _identity_store(config)
    observations_by_global = _global_observations_by_person(
        _result_store(config).list_global_observations()
    )
    matches: list[dict] = []
    for person in identity_store.people:
        similarity = float(np.dot(person.embedding, embedding))
        if similarity < threshold:
            continue
        observations = observations_by_global.get(person.global_person_id, [])
        representative_face_path = next(
            (
                observation.get("representative_face_path")
                for observation in observations
                if observation.get("representative_face_path")
            ),
            None,
        )
        matches.append(
            {
                "global_person_id": person.global_person_id,
                "similarity": similarity,
                "threshold": threshold,
                "is_strong_match": True,
                "query_face_confidence": detection.confidence,
                "label": observations[0].get("label") if observations else None,
                "representative_face_path": representative_face_path,
                "observation_count": len(observations),
                "observations": observations[:8],
            }
        )
    return sorted(matches, key=lambda item: item["similarity"], reverse=True)[:limit]


def _global_observations_by_person(rows: list[dict]) -> dict[str, list[dict]]:
    """按全局人物 ID 分组观测记录。"""
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(str(row["global_person_id"]), []).append(row)
    return grouped


def _face_search_quality(
    bbox_xyxy: tuple[float, float, float, float],
    confidence: float,
) -> tuple[float, float]:
    """图片搜索时优先选择置信度高、面积大的人脸。"""
    x1, y1, x2, y2 = bbox_xyxy
    return confidence, max(x2 - x1, 0.0) * max(y2 - y1, 0.0)


def _group_segment_rows_by_person(rows: list[dict]) -> dict[int, list[dict]]:
    """把 SQLite segment 行按人物 ID 分组。"""
    grouped: dict[int, list[dict]] = {}
    for row in rows:
        grouped.setdefault(int(row["person_id"]), []).append(row)
    return grouped


def _appearance_span_from_segment_row(row: dict) -> AppearanceSpan:
    """把 SQLite segment 行转为上下文算法输入。"""
    return AppearanceSpan(
        person_id=int(row["person_id"]),
        start=float(row["start"]),
        end=float(row["end"]),
        track_ids=_parse_track_ids(row.get("track_ids", "[]")),
        detection_count=int(row.get("detection_count", 0)),
        segment_id=int(row["id"]),
    )


def _context_segment_to_dict(segment: PersonContextSegment, label: str | None) -> dict:
    """把上下文片段转成 API JSON 响应。"""
    return {
        "person_id": segment.person_id,
        "label": label,
        "start": segment.start,
        "end": segment.end,
        "duration": segment.end - segment.start,
        "source_segment_count": segment.source_segment_count,
        "source_segment_ids": list(segment.source_segment_ids),
        "track_ids": list(segment.track_ids),
        "detection_count": segment.detection_count,
        "appearance_duration": segment.appearance_duration,
        "presence_ratio": segment.presence_ratio,
        "score": segment.score,
        "kind": segment.kind,
    }


def _parse_track_ids(raw: str) -> tuple[int, ...]:
    """解析 SQLite 中 JSON 字符串形式的 track_ids。"""
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return ()
    if not isinstance(parsed, list):
        return ()
    track_ids: set[int] = set()
    for value in parsed:
        try:
            track_ids.add(int(value))
        except (TypeError, ValueError):
            continue
    return tuple(sorted(track_ids))


def _enqueue_analyze_batch(request: AnalyzeBatchRequest) -> AnalyzeJobStatus:
    """校验本地视频路径并加入顺序分析队列。"""
    video_paths = _parse_video_paths(request.video_paths)
    if not video_paths:
        raise HTTPException(status_code=400, detail="Video paths must not be empty")
    if request.preset is not None and request.preset not in PRESET_NAMES:
        raise HTTPException(status_code=400, detail="Unsupported preset")
    config_path = _request_config_path(request)
    if config_path is not None and not config_path.exists():
        raise HTTPException(status_code=404, detail=f"Config file not found: {config_path}")

    missing = [path for path in video_paths if not Path(path).exists()]
    if missing:
        raise HTTPException(
            status_code=404,
            detail={"message": "Video path not found", "paths": missing},
        )

    job_id = uuid4().hex
    items = [
        AnalyzeJobItemStatus(
            video_path=path,
            status="queued",
            stage="queued",
            progress=0.0,
            message="等待开始分析",
        )
        for path in video_paths
    ]
    job = AnalyzeJobStatus(
        job_id=job_id,
        status="queued",
        stage="queued",
        progress=0.0,
        message=f"等待开始分析 {len(video_paths)} 个视频",
        video_path=video_paths[0] if len(video_paths) == 1 else None,
        video_paths=video_paths,
        total=len(video_paths),
        items=items,
    )
    with _ANALYSIS_JOBS_LOCK:
        _ANALYSIS_JOBS[job_id] = job.model_copy()
        _ANALYSIS_REQUESTS[job_id] = AnalyzeBatchRequest(
            video_paths=video_paths,
            preset=request.preset,
            use_cache=request.use_cache,
            expected_people_count=request.expected_people_count,
            display_title=request.display_title,
            series_name=request.series_name,
            original_filename=request.original_filename,
            source_path=request.source_path,
            source_directory=request.source_directory,
            hardware_profile=request.hardware_profile,
            allow_cpu_fallback=request.allow_cpu_fallback,
            config_path=request.config_path,
        )
        _ANALYSIS_CANCEL_EVENTS[job_id] = threading.Event()
    _persist_analysis_job(job)
    _ensure_analysis_worker_started()
    _ANALYSIS_QUEUE.put(job_id)
    return job


def _parse_video_paths(raw_paths: list[str] | str) -> list[str]:
    """解析数组或分号分隔的视频路径。"""
    if isinstance(raw_paths, str):
        candidates = raw_paths.replace("\n", ";").split(";")
    else:
        candidates = raw_paths

    paths: list[str] = []
    seen: set[str] = set()
    for raw in candidates:
        path = raw.strip().strip("\"'")
        if not path:
            continue
        if path in seen:
            continue
        seen.add(path)
        paths.append(path)
    return paths


def _ensure_analysis_worker_started() -> None:
    """确保分析队列工作线程已经启动。"""
    global _ANALYSIS_WORKER_STARTED
    with _ANALYSIS_WORKER_LOCK:
        if _ANALYSIS_WORKER_STARTED:
            return
        thread = threading.Thread(
            target=_analysis_worker_loop,
            daemon=True,
            name="analyze-queue",
        )
        thread.start()
        _ANALYSIS_WORKER_STARTED = True


def _analysis_worker_loop() -> None:
    """顺序执行分析队列，避免弱机器上并发抢占 CPU/GPU/内存。"""
    while True:
        job_id = _ANALYSIS_QUEUE.get()
        try:
            request = _get_analysis_request(job_id)
            if request is not None and not _is_analysis_canceled(job_id):
                _run_analyze_batch_job(job_id, request)
        finally:
            _ANALYSIS_QUEUE.task_done()


def _get_analysis_request(job_id: str) -> AnalyzeBatchRequest | None:
    """读取排队请求。"""
    with _ANALYSIS_JOBS_LOCK:
        request = _ANALYSIS_REQUESTS.get(job_id)
        return request.model_copy(deep=True) if request is not None else None


def _run_analyze_batch_job(job_id: str, request: AnalyzeBatchRequest) -> None:
    """顺序执行一个批量分析任务。"""
    video_paths = _parse_video_paths(request.video_paths)
    if _is_analysis_canceled(job_id):
        _mark_analysis_job_canceled(job_id, "分析任务已终止")
        return
    _update_analysis_job(
        job_id,
        status="running",
        stage="batch",
        progress=0.0,
        message=f"开始批量分析 {len(video_paths)} 个视频",
    )
    for index, video_path in enumerate(video_paths):
        if _is_analysis_canceled(job_id):
            _mark_remaining_analysis_items_canceled(job_id, start_index=index)
            break
        _update_analysis_item(
            job_id,
            index,
            status="running",
            stage="prepare",
            progress=0.0,
            message="准备视频与模型配置",
        )
        _update_analysis_job(
            job_id,
            status="running",
            stage="analyze",
            current_index=index,
            message=f"正在分析第 {index + 1}/{len(video_paths)} 个视频",
        )
        _run_analyze_job(
            job_id,
            AnalyzeRequest(
                video_path=video_path,
                preset=request.preset,
                use_cache=request.use_cache,
                expected_people_count=request.expected_people_count,
                display_title=request.display_title if len(video_paths) == 1 else None,
                series_name=request.series_name,
                original_filename=request.original_filename if len(video_paths) == 1 else None,
                source_path=request.source_path if len(video_paths) == 1 else None,
                source_directory=request.source_directory if len(video_paths) == 1 else None,
                hardware_profile=request.hardware_profile,
                allow_cpu_fallback=request.allow_cpu_fallback,
                config_path=request.config_path,
            ),
            item_index=index,
        )
        if _is_analysis_canceled(job_id):
            _mark_remaining_analysis_items_canceled(job_id, start_index=index + 1)
            break

    job = _get_analysis_job(job_id)
    if job is None:
        return
    if _is_analysis_canceled(job_id) or job.status == "canceled":
        _mark_analysis_job_canceled(job_id, "分析任务已终止")
        return
    final_status = "failed" if job.failed == job.total else "succeeded"
    message = f"批量分析完成：成功 {job.completed} 个，失败 {job.failed} 个"
    _update_analysis_job(
        job_id,
        status=final_status,
        stage="done",
        progress=1.0,
        message=message,
        current_index=None,
    )
    _drop_analysis_runtime_state(job_id)


def _run_analyze_job(
    job_id: str,
    request: AnalyzeRequest,
    item_index: int = 0,
) -> None:
    """在后台线程中执行分析任务，并更新进度快照。"""
    try:
        _update_analysis_item(
            job_id,
            item_index,
            status="running",
            stage="prepare",
            progress=0.03,
            message="准备视频与模型配置",
        )
        video_path = Path(request.video_path)
        next_config = _analysis_config(request)
        analysis_path, source_metadata = _prepare_analysis_media(video_path, request, next_config)
        progress_factory = _AnalysisProgressFactory(job_id, item_index)
        timeline_path = FaceVideoPipeline(
            next_config,
            progress_factory=progress_factory,
            should_cancel=lambda: _is_analysis_canceled(job_id),
        ).run(
            analysis_path,
            preset=request.preset,
            use_cache=request.use_cache,
            output_name=source_metadata.get("original_filename"),
        )
        _raise_if_analysis_canceled(job_id)
        _update_analysis_item(
            job_id,
            item_index,
            stage="database",
            progress=0.92,
            message="写入本地结果库",
        )
        video_id = _result_store(next_config).import_timeline(
            timeline_path,
            display_title=request.display_title,
            series_name=request.series_name,
            **source_metadata,
        )
        _update_analysis_item(
            job_id,
            item_index,
            status="succeeded",
            stage="done",
            progress=1.0,
            message="分析完成",
            video_id=video_id,
            timeline_path=str(timeline_path),
        )
    except PipelineCancelled:
        _update_analysis_item(
            job_id,
            item_index,
            status="canceled",
            stage="canceled",
            progress=1.0,
            message="分析已终止",
        )
    except Exception as exc:  # pragma: no cover - 具体异常由依赖和视频文件决定
        if _is_analysis_canceled(job_id):
            _update_analysis_item(
                job_id,
                item_index,
                status="canceled",
                stage="canceled",
                progress=1.0,
                message="分析已终止",
            )
            return
        _update_analysis_item(
            job_id,
            item_index,
            status="failed",
            stage="failed",
            progress=1.0,
            message="分析失败",
            error=str(exc),
        )


class _AnalysisProgressFactory:
    """把 pipeline 的逐帧迭代进度映射到 API 任务状态。"""

    def __init__(self, job_id: str, item_index: int) -> None:
        self.job_id = job_id
        self.item_index = item_index

    def __call__(self, iterable, **kwargs):
        total = int(kwargs.get("total") or 0)
        desc = str(kwargs.get("desc") or "analyze")
        if desc == "analyze":
            _update_analysis_item(
                self.job_id,
                self.item_index,
                status="running",
                stage="analyze",
                progress=0.08,
                message="正在检测人脸与提取特征",
            )
        last_percent = -1
        for index, item in enumerate(iterable, start=1):
            _raise_if_analysis_canceled(self.job_id)
            yield item
            _raise_if_analysis_canceled(self.job_id)
            if total <= 0:
                continue
            percent = int((index / total) * 100)
            if percent == last_percent:
                continue
            last_percent = percent
            progress = min(0.86, 0.08 + (index / total) * 0.78)
            _update_analysis_item(
                self.job_id,
                self.item_index,
                status="running",
                stage="analyze",
                progress=progress,
                message=f"正在分析采样帧 {index}/{total}",
            )


def _cancel_analysis_job(job_id: str) -> AnalyzeJobStatus | None:
    """标记任务取消，并通知正在运行的 pipeline 尽快退出。"""
    with _ANALYSIS_JOBS_LOCK:
        job = _ANALYSIS_JOBS.get(job_id)
        if job is None:
            persisted = _result_store().get_analyze_job(job_id)
            if persisted is None:
                return None
            job = AnalyzeJobStatus.model_validate(persisted)
            _ANALYSIS_JOBS[job_id] = job
        event = _ANALYSIS_CANCEL_EVENTS.setdefault(job_id, threading.Event())
        event.set()
    if job.status in {"succeeded", "failed", "canceled"}:
        return job.model_copy()
    _mark_analysis_job_canceled(job_id, "分析任务已终止")
    canceled = _get_analysis_job(job_id)
    return canceled


def _is_analysis_canceled(job_id: str) -> bool:
    """判断任务是否已经收到取消请求。"""
    with _ANALYSIS_JOBS_LOCK:
        event = _ANALYSIS_CANCEL_EVENTS.get(job_id)
        job = _ANALYSIS_JOBS.get(job_id)
        return bool(event and event.is_set()) or job is not None and job.status == "canceled"


def _raise_if_analysis_canceled(job_id: str) -> None:
    """收到取消请求时抛出 pipeline 可识别的取消异常。"""
    if _is_analysis_canceled(job_id):
        raise PipelineCancelled("analysis canceled")


def _mark_remaining_analysis_items_canceled(job_id: str, start_index: int) -> None:
    """把尚未执行的批量子任务标记为已终止。"""
    with _ANALYSIS_JOBS_LOCK:
        job = _ANALYSIS_JOBS.get(job_id)
        if job is None:
            return
        items = [item.model_copy() for item in job.items]
        for index in range(start_index, len(items)):
            if items[index].status in {"queued", "running"}:
                items[index] = AnalyzeJobItemStatus.model_validate(
                    {
                        **items[index].model_dump(),
                        "status": "canceled",
                        "stage": "canceled",
                        "progress": 1.0,
                        "message": "分析已终止",
                    }
                )
        payload = job.model_dump()
        payload["items"] = [item.model_dump() for item in items]
        _ANALYSIS_JOBS[job_id] = AnalyzeJobStatus.model_validate(payload)


def _mark_analysis_job_canceled(job_id: str, message: str) -> None:
    """把整个任务快照写成终止状态。"""
    next_job: AnalyzeJobStatus | None = None
    with _ANALYSIS_JOBS_LOCK:
        job = _ANALYSIS_JOBS.get(job_id)
        if job is None:
            return
        items = []
        for item in job.items:
            if item.status in {"succeeded", "failed"}:
                items.append(item)
            else:
                items.append(
                    AnalyzeJobItemStatus.model_validate(
                        {
                            **item.model_dump(),
                            "status": "canceled",
                            "stage": "canceled",
                            "progress": 1.0,
                            "message": "分析已终止",
                        }
                    )
                )
        payload = job.model_dump()
        payload.update(
            {
                "status": "canceled",
                "stage": "canceled",
                "progress": 1.0,
                "message": message,
                "current_index": None,
                "items": [item.model_dump() for item in items],
            }
        )
        next_job = AnalyzeJobStatus.model_validate(payload)
        _ANALYSIS_JOBS[job_id] = next_job
    if next_job is not None:
        _persist_analysis_job(next_job)
    _drop_analysis_runtime_state(job_id)


def _drop_analysis_runtime_state(job_id: str) -> None:
    """清理已完成任务的内存运行态。"""
    with _ANALYSIS_JOBS_LOCK:
        _ANALYSIS_REQUESTS.pop(job_id, None)
        _ANALYSIS_CANCEL_EVENTS.pop(job_id, None)


def _set_analysis_job(job: AnalyzeJobStatus) -> None:
    """写入任务状态快照。"""
    with _ANALYSIS_JOBS_LOCK:
        _ANALYSIS_JOBS[job.job_id] = job.model_copy()
    _persist_analysis_job(job)


def _get_analysis_job(job_id: str) -> AnalyzeJobStatus | None:
    """读取任务状态快照。"""
    with _ANALYSIS_JOBS_LOCK:
        job = _ANALYSIS_JOBS.get(job_id)
    if job is not None:
        return job.model_copy()
    persisted = _result_store().get_analyze_job(job_id)
    return AnalyzeJobStatus.model_validate(persisted) if persisted is not None else None


def _update_analysis_job(job_id: str, **changes) -> None:
    """局部更新任务状态快照。"""
    next_job: AnalyzeJobStatus | None = None
    with _ANALYSIS_JOBS_LOCK:
        job = _ANALYSIS_JOBS.get(job_id)
        if job is None:
            return
        if job.status == "canceled" and changes.get("status") != "canceled":
            return
        payload = job.model_dump()
        payload.update(changes)
        progress = payload.get("progress")
        if isinstance(progress, int | float):
            payload["progress"] = max(0.0, min(float(progress), 1.0))
        next_job = AnalyzeJobStatus.model_validate(payload)
        _ANALYSIS_JOBS[job_id] = next_job
    if next_job is not None:
        _persist_analysis_job(next_job)


def _update_analysis_item(job_id: str, item_index: int, **changes) -> None:
    """更新批量任务中的单个视频状态，并同步汇总进度。"""
    next_job: AnalyzeJobStatus | None = None
    with _ANALYSIS_JOBS_LOCK:
        job = _ANALYSIS_JOBS.get(job_id)
        if job is None or item_index < 0 or item_index >= len(job.items):
            return
        if job.status == "canceled" and changes.get("status") != "canceled":
            return
        items = [item.model_copy() for item in job.items]
        item_payload = items[item_index].model_dump()
        item_payload.update(changes)
        item_progress = item_payload.get("progress")
        if isinstance(item_progress, int | float):
            item_payload["progress"] = max(0.0, min(float(item_progress), 1.0))
        items[item_index] = AnalyzeJobItemStatus.model_validate(item_payload)

        completed = sum(1 for item in items if item.status == "succeeded")
        failed = sum(1 for item in items if item.status == "failed")
        running_item = items[item_index]
        total = max(len(items), 1)
        aggregate_progress = sum(item.progress for item in items) / total

        payload = job.model_dump()
        payload.update(
            {
                "items": [item.model_dump() for item in items],
                "completed": completed,
                "failed": failed,
                "current_index": item_index
                if running_item.status in {"queued", "running"}
                else payload.get("current_index"),
                "video_id": running_item.video_id or payload.get("video_id"),
                "timeline_path": running_item.timeline_path or payload.get("timeline_path"),
                "error": running_item.error or payload.get("error"),
                "progress": max(0.0, min(aggregate_progress, 1.0)),
            }
        )
        if running_item.status == "running":
            payload["status"] = "running"
            payload["stage"] = running_item.stage
            payload["message"] = (
                f"第 {item_index + 1}/{total} 个视频：{running_item.message}"
                if total > 1
                else running_item.message
            )
        next_job = AnalyzeJobStatus.model_validate(payload)
        _ANALYSIS_JOBS[job_id] = next_job
    if next_job is not None:
        _persist_analysis_job(next_job)


def _persist_analysis_job(job: AnalyzeJobStatus) -> None:
    """把任务状态写入 SQLite。"""
    try:
        _result_store().save_analyze_job(job.model_dump())
    except Exception:
        # 状态持久化失败不能中断正在进行的视频分析。
        return


app = create_app()

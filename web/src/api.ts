/** 视频列表和详情页共用的视频摘要。 */
export type VideoItem = {
  id: number;
  path: string;
  title: string;
  fps: number;
  frame_count: number;
  width: number;
  height: number;
  duration_seconds: number;
  people_count: number;
  timeline_path: string;
  original_filename: string | null;
  series_name: string;
  source_path: string | null;
  source_directory: string;
  analysis_elapsed_seconds: number | null;
  deleted_at: string | null;
};

/** 单个视频内聚类出来的人物记录。 */
export type PersonItem = {
  id: number;
  video_id: number;
  person_id: number;
  label: string;
  global_person_id: string | null;
  appearances: number;
  total_duration: number;
  detection_count: number;
  representative_face_path: string | null;
  representative_timestamp: number | null;
  representative_frame_index: number | null;
  hidden: number;
};

/** 人脸跟踪轨迹的聚合信息。 */
export type TrackItem = {
  id: number;
  video_id: number;
  track_id: number;
  person_id: number | null;
  start: number;
  end: number;
  detection_count: number;
  representative_face_path: string | null;
  representative_bbox_json: string;
  representative_confidence: number | null;
  representative_timestamp: number | null;
  representative_frame_index: number | null;
  embedding_dim: number;
  embedding_norm: number;
};

/** 逐帧检测到的人脸框。 */
export type TrackDetectionItem = {
  id: number;
  video_id: number;
  track_id: number;
  person_id: number | null;
  frame_index: number;
  timestamp: number;
  bbox_json: string;
  confidence: number | null;
};

/** 后端导出的代表脸或轨迹截图。 */
export type FaceCropItem = {
  id: number;
  video_id: number;
  person_id: number | null;
  track_id: number | null;
  path: string;
  source: string;
  confidence: number | null;
  timestamp: number | null;
  frame_index: number | null;
  bbox_json: string | null;
};

/** 跨视频合并后的人物档案。 */
export type GlobalPersonItem = {
  global_person_id: string;
  label: string | null;
  representative_face_path: string | null;
  representative_timestamp: number | null;
  representative_frame_index: number | null;
  observation_count: number;
  confirmed_count: number;
  total_duration: number;
  four_view_asset_count: number;
  deleted_at: string | null;
};

/** 人物档案操作历史。 */
export type GlobalPersonActionItem = {
  id: number;
  global_person_id: string;
  action: string;
  payload: Record<string, unknown>;
  created_at: string;
};

/** 人物档案在某个视频中的一次本地观测。 */
export type GlobalObservationItem = {
  id: number;
  global_person_id: string;
  video_id: number | null;
  video_path: string;
  local_person_id: number;
  label: string;
  representative_face_path: string | null;
  representative_timestamp: number | null;
  representative_frame_index: number | null;
  appearances: number;
  total_duration: number;
  detection_count: number;
  confirmed: number;
  rejected: number;
  hidden: number;
  video_title: string | null;
  series_name: string | null;
  original_filename: string | null;
  source_path: string | null;
  source_directory: string | null;
};

/** 人物档案下的一张未切分四视图原图资产。 */
export type FourViewAssetItem = {
  id: number;
  global_person_id: string;
  label: string;
  image_path: string;
  reference_count: number;
  created_at: string;
};

/** 送给图像生成服务的一张参考素材。 */
export type FourViewReferenceInput = {
  video_id: number | null;
  frame_index: number | null;
  timestamp: number | null;
  face_path: string | null;
  label: string | null;
};

/** 四视图生成请求。 */
export type GenerateFourViewRequest = {
  label?: string | null;
  prompt?: string | null;
  references: FourViewReferenceInput[];
};

/** 时间轴上同一人物的一段出现区间。 */
export type SegmentItem = {
  id: number;
  video_id: number;
  person_id: number;
  start: number;
  end: number;
  detection_count: number;
  track_ids: string;
  clip_path: string | null;
};

/** 视频详情包含人物、片段、轨迹和截图集合。 */
export type VideoDetail = VideoItem & {
  people: PersonItem[];
  segments: SegmentItem[];
  tracks: TrackItem[];
  face_crops: FaceCropItem[];
};

/** 上传视频接口返回的素材定位信息。 */
export type UploadVideoResponse = {
  video_path: string;
  filename: string;
  source_path: string;
  source_directory: string;
  size: number;
};

/** 可选的本地推理硬件配置。 */
export type HardwareProfileId = "auto" | "cpu" | "apple" | "nvidia" | "intel";

/** 单个硬件配置的 provider 和可用性说明。 */
export type HardwareProfileItem = {
  id: HardwareProfileId;
  label: string;
  preferred_providers: string[];
  note: string;
  available: boolean;
};

/** 后端探测到的运行环境和推荐硬件配置。 */
export type HardwareSummary = {
  system: string;
  machine: string;
  processor: string;
  python: string;
  nvidia_smi: string | null;
  gpu_devices: string[];
  available_providers: string[];
  recommended_profile: HardwareProfileId;
  recommended_providers: string[];
  profiles: HardwareProfileItem[];
};

/** 同步分析接口的完成结果。 */
export type AnalyzeVideoResponse = {
  video_id: number;
  timeline_path: string;
};

/** 后台分析任务的实时状态。 */
export type AnalyzeJobStatus = {
  job_id: string;
  status: "queued" | "running" | "succeeded" | "failed" | "canceled";
  stage: string;
  progress: number;
  message: string;
  video_id: number | null;
  timeline_path: string | null;
  error: string | null;
  video_path: string | null;
  video_paths: string[];
  total: number;
  completed: number;
  failed: number;
  current_index: number | null;
  items: AnalyzeJobItemStatus[];
  created_at: string | null;
  updated_at: string | null;
};

/** 批量分析任务中单个视频的状态。 */
export type AnalyzeJobItemStatus = {
  video_path: string;
  status: "queued" | "running" | "succeeded" | "failed" | "canceled";
  stage: string;
  progress: number;
  message: string;
  video_id: number | null;
  timeline_path: string | null;
  error: string | null;
};

/** 导入时间轴接口返回的新视频 ID。 */
export type ImportTimelineResponse = {
  video_id: number;
};

/** 更新作品元数据时可提交的字段。 */
export type UpdateVideoRequest = {
  title?: string | null;
  series_name?: string | null;
  original_filename?: string | null;
  source_path?: string | null;
  source_directory?: string | null;
};

/** 文本搜索命中的本地人物结果。 */
export type PeopleSearchResult = {
  id: number;
  video_id: number;
  person_id: number;
  label: string;
  global_person_id: string | null;
  appearances: number;
  total_duration: number;
  detection_count: number;
  representative_face_path: string | null;
  video_title: string;
  video_path: string;
  series_name: string;
  source_path: string | null;
  source_directory: string | null;
  duration_seconds: number;
  global_label: string | null;
  observation_count: number | null;
  confirmed_count: number | null;
};

/** 以图搜图命中的全局人物结果。 */
export type FaceSearchResult = {
  global_person_id: string;
  similarity: number;
  threshold: number;
  is_strong_match: boolean;
  query_face_confidence: number | null;
  label: string | null;
  representative_face_path: string | null;
  observation_count: number;
  observations: GlobalObservationItem[];
};

/** 读取 FastAPI 返回的 detail，避免前端把真实失败原因吞掉。 */
async function apiErrorMessage(response: Response, fallback: string) {
  try {
    const payload = await response.json();
    if (typeof payload?.detail === "string" && payload.detail.trim()) {
      return `${fallback}：${payload.detail.trim()}`;
    }
  } catch {
    // 非 JSON 响应时使用调用方提供的兜底文案。
  }
  return fallback;
}

/** 读取视频列表，可按回收站状态筛选。 */
export async function listVideos(options: { includeDeleted?: boolean; onlyDeleted?: boolean } = {}): Promise<VideoItem[]> {
  const params = new URLSearchParams();
  if (options.includeDeleted) params.set("include_deleted", "true");
  if (options.onlyDeleted) params.set("only_deleted", "true");
  const query = params.toString();
  const response = await fetch(`/api/videos${query ? `?${query}` : ""}`);
  if (!response.ok) throw new Error("无法读取视频列表");
  return response.json();
}

/** 读取指定视频的完整分析详情。 */
export async function getVideo(id: number): Promise<VideoDetail> {
  const response = await fetch(`/api/videos/${id}`);
  if (!response.ok) throw new Error("无法读取视频详情");
  return response.json();
}

/** 读取指定视频的逐帧人脸检测框。 */
export async function listTrackDetections(videoId: number): Promise<TrackDetectionItem[]> {
  const response = await fetch(`/api/videos/${videoId}/track-detections`);
  if (!response.ok) throw new Error("无法读取逐帧人脸框");
  return response.json();
}

/** 上传本地视频文件到后端素材区。 */
export async function uploadVideo(file: File): Promise<UploadVideoResponse> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch("/api/upload-video", {
    method: "POST",
    body: form
  });
  if (!response.ok) throw new Error("无法上传视频");
  return response.json();
}

/** 读取后端硬件探测和 provider 推荐结果。 */
export async function getHardware(): Promise<HardwareSummary> {
  const response = await fetch("/api/hardware");
  if (!response.ok) throw new Error("无法读取硬件信息");
  return response.json();
}

/** 触发单视频同步分析。 */
export async function analyzeVideo(
  videoPath: string,
  preset = "fast",
  useCache = true,
  expectedPeopleCount: number | null = null,
  displayTitle: string | null = null,
  seriesName: string | null = null,
  originalFilename: string | null = null,
  sourcePath: string | null = null,
  sourceDirectory: string | null = null,
  hardwareProfile: HardwareProfileId = "auto",
  allowCpuFallback = true,
  configPath: string | null = null
): Promise<AnalyzeVideoResponse> {
  const response = await fetch("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      video_path: videoPath,
      preset,
      use_cache: useCache,
      expected_people_count: expectedPeopleCount,
      display_title: displayTitle,
      series_name: seriesName,
      original_filename: originalFilename,
      source_path: sourcePath,
      source_directory: sourceDirectory,
      hardware_profile: hardwareProfile,
      allow_cpu_fallback: allowCpuFallback,
      config_path: configPath
    })
  });
  if (!response.ok) throw new Error("无法分析视频");
  return response.json();
}

/** 创建单视频后台分析任务。 */
export async function startAnalyzeJob(
  videoPath: string,
  preset = "fast",
  useCache = true,
  expectedPeopleCount: number | null = null,
  displayTitle: string | null = null,
  seriesName: string | null = null,
  originalFilename: string | null = null,
  sourcePath: string | null = null,
  sourceDirectory: string | null = null,
  hardwareProfile: HardwareProfileId = "auto",
  allowCpuFallback = true,
  configPath: string | null = null
): Promise<AnalyzeJobStatus> {
  const response = await fetch("/api/analyze-jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      video_path: videoPath,
      preset,
      use_cache: useCache,
      expected_people_count: expectedPeopleCount,
      display_title: displayTitle,
      series_name: seriesName,
      original_filename: originalFilename,
      source_path: sourcePath,
      source_directory: sourceDirectory,
      hardware_profile: hardwareProfile,
      allow_cpu_fallback: allowCpuFallback,
      config_path: configPath
    })
  });
  if (!response.ok) throw new Error("无法启动分析任务");
  return response.json();
}

/** 创建批量视频后台分析任务。 */
export async function startAnalyzeBatchJob(
  videoPaths: string[] | string,
  preset = "fast",
  useCache = true,
  expectedPeopleCount: number | null = null,
  seriesName: string | null = null,
  hardwareProfile: HardwareProfileId = "auto",
  allowCpuFallback = true,
  configPath: string | null = null
): Promise<AnalyzeJobStatus> {
  const response = await fetch("/api/analyze-batch-jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      video_paths: videoPaths,
      preset,
      use_cache: useCache,
      expected_people_count: expectedPeopleCount,
      series_name: seriesName,
      hardware_profile: hardwareProfile,
      allow_cpu_fallback: allowCpuFallback,
      config_path: configPath
    })
  });
  if (!response.ok) throw new Error("无法启动批量分析任务");
  return response.json();
}

/** 查询后台分析任务的当前进度。 */
export async function getAnalyzeJob(jobId: string): Promise<AnalyzeJobStatus> {
  const response = await fetch(`/api/analyze-jobs/${jobId}`);
  if (!response.ok) throw new Error("无法读取分析进度");
  return response.json();
}

/** 读取最近的后台分析任务列表。 */
export async function listAnalyzeJobs(limit = 10): Promise<AnalyzeJobStatus[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  const response = await fetch(`/api/analyze-jobs?${params.toString()}`);
  if (!response.ok) throw new Error("无法读取分析任务列表");
  return response.json();
}

/** 请求后端终止后台分析任务。 */
export async function cancelAnalyzeJob(jobId: string): Promise<AnalyzeJobStatus> {
  const response = await fetch(`/api/analyze-jobs/${jobId}/cancel`, {
    method: "POST"
  });
  if (!response.ok) throw new Error("无法终止分析任务");
  return response.json();
}

/** 按关键词搜索本地人物库。 */
export async function searchPeople(q: string, limit = 50): Promise<PeopleSearchResult[]> {
  const params = new URLSearchParams({ q, limit: String(limit) });
  const response = await fetch(`/api/search/people?${params.toString()}`);
  if (!response.ok) throw new Error("无法搜索人物");
  return response.json();
}

/** 上传人脸图片并搜索相似的全局人物。 */
export async function searchFaces(
  file: File,
  limit = 10,
  minSimilarity?: number
): Promise<FaceSearchResult[]> {
  const form = new FormData();
  form.append("file", file);
  const params = new URLSearchParams({ limit: String(limit) });
  if (minSimilarity !== undefined) params.set("min_similarity", String(minSimilarity));
  const response = await fetch(`/api/search/faces?${params.toString()}`, {
    method: "POST",
    body: form
  });
  if (!response.ok) throw new Error("无法以图搜图");
  return response.json();
}

/** 生成某个视频指定帧的完整画面 URL。 */
export function videoFrameUrl(
  videoId: number,
  options: { frameIndex?: number | null; timestamp?: number | null }
): string {
  const params = new URLSearchParams();
  if (options.frameIndex !== undefined && options.frameIndex !== null) {
    params.set("frame_index", String(options.frameIndex));
  } else if (options.timestamp !== undefined && options.timestamp !== null) {
    params.set("timestamp", String(options.timestamp));
  }
  return `/api/videos/${videoId}/frame?${params.toString()}`;
}

/** 从后端可访问路径导入 timeline.json。 */
export async function importTimeline(timelinePath: string): Promise<ImportTimelineResponse> {
  const response = await fetch("/api/import-timeline", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ timeline_path: timelinePath })
  });
  if (!response.ok) throw new Error("无法导入时间轴");
  return response.json();
}

/** 保存视频作品的展示元数据。 */
export async function updateVideo(
  videoId: number,
  payload: UpdateVideoRequest
): Promise<VideoItem> {
  const response = await fetch(`/api/videos/${videoId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) throw new Error("无法更新视频作品信息");
  return response.json();
}

/** 将视频素材移入回收站。 */
export async function trashVideo(videoId: number): Promise<VideoItem> {
  const response = await fetch(`/api/videos/${videoId}`, {
    method: "DELETE"
  });
  if (!response.ok) throw new Error("无法移入回收站");
  return response.json();
}

/** 从回收站恢复视频素材。 */
export async function restoreVideo(videoId: number): Promise<VideoItem> {
  const response = await fetch(`/api/videos/${videoId}/restore`, {
    method: "POST"
  });
  if (!response.ok) throw new Error("无法从回收站恢复");
  return response.json();
}

/** 彻底删除视频的分析数据。 */
export async function purgeVideo(videoId: number): Promise<{ status: string }> {
  const response = await fetch(`/api/videos/${videoId}/purge`, {
    method: "DELETE"
  });
  if (!response.ok) throw new Error("无法彻底删除素材数据");
  return response.json();
}

/** 重命名单个视频内的人物。 */
export async function renamePerson(
  videoId: number,
  personId: number,
  label: string
): Promise<VideoDetail> {
  const response = await fetch(`/api/videos/${videoId}/people/${personId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ label })
  });
  if (!response.ok) throw new Error("无法命名人物");
  return response.json();
}

/** 将本地人物合并到目标人物。 */
export async function mergePeople(
  videoId: number,
  sourcePersonId: number,
  targetPersonId: number
): Promise<VideoDetail> {
  const response = await fetch(`/api/videos/${videoId}/people/merge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      source_person_id: sourcePersonId,
      target_person_id: targetPersonId
    })
  });
  if (!response.ok) throw new Error("无法合并人物");
  return response.json();
}

/** 从人物中拆出指定轨迹生成新人。 */
export async function splitTracks(
  videoId: number,
  sourcePersonId: number,
  trackIds: number[],
  label?: string
): Promise<VideoDetail & { new_person_id: number }> {
  const response = await fetch(`/api/videos/${videoId}/people/split`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      source_person_id: sourcePersonId,
      track_ids: trackIds,
      label
    })
  });
  if (!response.ok) throw new Error("无法拆分人物");
  return response.json();
}

/** 将指定轨迹批量归类到目标人物。 */
export async function assignTracks(
  videoId: number,
  trackIds: number[],
  targetPersonId: number
): Promise<VideoDetail> {
  const response = await fetch(`/api/videos/${videoId}/tracks/assign`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      track_ids: trackIds,
      target_person_id: targetPersonId
    })
  });
  if (!response.ok) throw new Error("无法批量归类轨迹");
  return response.json();
}

/** 删除误检轨迹并刷新视频详情。 */
export async function deleteTracks(videoId: number, trackIds: number[]): Promise<VideoDetail> {
  const response = await fetch(`/api/videos/${videoId}/tracks`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ track_ids: trackIds })
  });
  if (!response.ok) throw new Error("无法删除误检轨迹");
  return response.json();
}

/** 将本地人物关联到已有全局人物档案。 */
export async function linkPersonToGlobal(
  videoId: number,
  personId: number,
  globalPersonId: string
): Promise<VideoDetail> {
  const response = await fetch(`/api/videos/${videoId}/people/${personId}/global-link`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ global_person_id: globalPersonId })
  });
  if (!response.ok) throw new Error("无法关联人物档案");
  return response.json();
}

/** 基于本地人物创建新的全局人物档案。 */
export async function createGlobalPersonFromLocal(
  videoId: number,
  personId: number,
  label: string | null = null
): Promise<VideoDetail & { global_person_id: string }> {
  const response = await fetch(`/api/videos/${videoId}/people/${personId}/global-person`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ label })
  });
  if (!response.ok) throw new Error("无法新建人物档案");
  return response.json();
}

/** 删除视频内的人物及其关联轨迹。 */
export async function deletePerson(videoId: number, personId: number): Promise<VideoDetail> {
  const response = await fetch(`/api/videos/${videoId}/people/${personId}`, {
    method: "DELETE"
  });
  if (!response.ok) throw new Error("无法删除人物");
  return response.json();
}

type ListGlobalPeopleOptions = {
  includeHidden?: boolean;
  includeDeleted?: boolean;
  onlyDeleted?: boolean;
};

/** 读取跨视频人物档案列表。 */
export async function listGlobalPeople(
  options: boolean | ListGlobalPeopleOptions = false
): Promise<GlobalPersonItem[]> {
  const nextOptions = typeof options === "boolean" ? { includeHidden: options } : options;
  const params = new URLSearchParams();
  if (nextOptions.includeHidden) params.set("include_hidden", "true");
  if (nextOptions.includeDeleted) params.set("include_deleted", "true");
  if (nextOptions.onlyDeleted) params.set("only_deleted", "true");
  const query = params.toString();
  const response = await fetch(`/api/global-people${query ? `?${query}` : ""}`);
  if (!response.ok) throw new Error("无法读取人物档案库");
  return response.json();
}

/** 手动创建一个空白人物档案。 */
export async function createManualGlobalPerson(
  label: string
): Promise<{ global_person_id: string; global_people: GlobalPersonItem[] }> {
  const response = await fetch("/api/global-people", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ label })
  });
  if (!response.ok) throw new Error("无法手动新建人物档案");
  return response.json();
}

/** 把一个人物档案移入回收站。 */
export async function deleteGlobalPerson(
  globalPersonId: string
): Promise<{ global_people: GlobalPersonItem[]; deleted_global_people: GlobalPersonItem[] }> {
  const response = await fetch(`/api/global-people/${globalPersonId}`, {
    method: "DELETE"
  });
  if (!response.ok) throw new Error("无法删除人物档案");
  return response.json();
}

/** 从回收站恢复人物档案。 */
export async function restoreGlobalPerson(
  globalPersonId: string
): Promise<{ global_people: GlobalPersonItem[]; deleted_global_people: GlobalPersonItem[] }> {
  const response = await fetch(`/api/global-people/${globalPersonId}/restore`, {
    method: "POST"
  });
  if (!response.ok) throw new Error("无法恢复人物档案");
  return response.json();
}

/** 彻底删除一个人物档案，并解除本地人物关联。 */
export async function purgeGlobalPerson(
  globalPersonId: string
): Promise<{ global_people: GlobalPersonItem[]; deleted_global_people: GlobalPersonItem[] }> {
  const response = await fetch(`/api/global-people/${globalPersonId}/purge`, {
    method: "DELETE"
  });
  if (!response.ok) throw new Error("无法彻底删除人物档案");
  return response.json();
}

/** 重命名人物档案的全局展示名称。 */
export async function renameGlobalPerson(
  globalPersonId: string,
  label: string
): Promise<{ global_person_id: string; global_people: GlobalPersonItem[] }> {
  const response = await fetch(`/api/global-people/${globalPersonId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ label })
  });
  if (!response.ok) throw new Error("无法重命名人物档案");
  return response.json();
}

/** 读取人物档案操作历史。 */
export async function listGlobalPersonActions(
  globalPersonId?: string,
  limit = 50
): Promise<GlobalPersonActionItem[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (globalPersonId) params.set("global_person_id", globalPersonId);
  const response = await fetch(`/api/global-person-actions?${params.toString()}`);
  if (!response.ok) throw new Error("无法读取人物档案操作历史");
  return response.json();
}

/** 把源人物档案合并进目标人物档案，保留目标 ID。 */
export async function mergeGlobalPeople(
  targetGlobalPersonId: string,
  sourceGlobalPersonId: string
): Promise<{
  global_people: GlobalPersonItem[];
  observations: GlobalObservationItem[];
  four_view_assets: FourViewAssetItem[];
}> {
  const response = await fetch(`/api/global-people/${targetGlobalPersonId}/merge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source_global_person_id: sourceGlobalPersonId })
  });
  if (!response.ok) throw new Error("无法合并人物档案");
  return response.json();
}

/** 读取某个全局人物的所有本地观测。 */
export async function listGlobalObservations(
  globalPersonId: string,
  includeHidden = false
): Promise<GlobalObservationItem[]> {
  const params = new URLSearchParams();
  if (includeHidden) params.set("include_hidden", "true");
  const query = params.toString();
  const response = await fetch(
    `/api/global-people/${globalPersonId}/observations${query ? `?${query}` : ""}`
  );
  if (!response.ok) throw new Error("无法读取跨视频观测");
  return response.json();
}

/** 读取人物档案下的四视图原图资产。 */
export async function listFourViewAssets(globalPersonId: string): Promise<FourViewAssetItem[]> {
  const response = await fetch(`/api/global-people/${globalPersonId}/four-view-assets`);
  if (!response.ok) throw new Error("无法读取四视图资产");
  return response.json();
}

/** 上传一张未切分的四视图原图。 */
export async function uploadFourViewAsset(
  globalPersonId: string,
  file: File,
  label: string | null = null
): Promise<FourViewAssetItem> {
  const body = new FormData();
  body.append("file", file);
  if (label?.trim()) body.append("label", label.trim());
  const response = await fetch(`/api/global-people/${globalPersonId}/four-view-assets`, {
    method: "POST",
    body
  });
  if (!response.ok) throw new Error("无法上传四视图资产");
  return response.json();
}

/** 基于选中的参考素材生成一张未切分四视图原图。 */
export async function generateFourViewAsset(
  globalPersonId: string,
  payload: GenerateFourViewRequest
): Promise<FourViewAssetItem> {
  const response = await fetch(`/api/global-people/${globalPersonId}/four-view-assets/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) throw new Error(await apiErrorMessage(response, "无法生成四视图资产"));
  return response.json();
}

/** 删除人物档案下的一张四视图原图资产。 */
export async function deleteFourViewAsset(
  globalPersonId: string,
  assetId: number
): Promise<{
  deleted_asset: FourViewAssetItem;
  four_view_assets: FourViewAssetItem[];
  global_people: GlobalPersonItem[];
}> {
  const response = await fetch(`/api/global-people/${globalPersonId}/four-view-assets/${assetId}`, {
    method: "DELETE"
  });
  if (!response.ok) throw new Error(await apiErrorMessage(response, "无法删除四视图资产"));
  return response.json();
}

/** 把一个人物档案下的四视图资产整体迁移到另一个人物档案。 */
export async function moveFourViewAssets(
  sourceGlobalPersonId: string,
  targetGlobalPersonId: string
): Promise<{
  moved_assets: FourViewAssetItem[];
  source_four_view_assets: FourViewAssetItem[];
  target_four_view_assets: FourViewAssetItem[];
  global_people: GlobalPersonItem[];
}> {
  const response = await fetch(`/api/global-people/${sourceGlobalPersonId}/four-view-assets/move`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target_global_person_id: targetGlobalPersonId })
  });
  if (!response.ok) throw new Error(await apiErrorMessage(response, "无法迁移四视图资产"));
  return response.json();
}

/** 更新视频内人物的显示或隐藏状态。 */
export async function setPersonHidden(
  videoId: number,
  personId: number,
  hidden: boolean
): Promise<VideoDetail> {
  const response = await fetch(`/api/videos/${videoId}/people/${personId}/visibility`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ hidden })
  });
  if (!response.ok) throw new Error("无法更新人物显示状态");
  return response.json();
}

/** 确认本地观测属于当前全局人物。 */
export async function confirmGlobalObservation(
  globalPersonId: string,
  videoPath: string,
  localPersonId: number
) {
  const response = await fetch(`/api/global-people/${globalPersonId}/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      video_path: videoPath,
      local_person_id: localPersonId
    })
  });
  if (!response.ok) throw new Error("无法确认人物档案");
  return response.json();
}

/** 驳回本地观测并从当前全局人物拆分。 */
export async function rejectGlobalObservation(
  globalPersonId: string,
  videoPath: string,
  localPersonId: number
) {
  const response = await fetch(`/api/global-people/${globalPersonId}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      video_path: videoPath,
      local_person_id: localPersonId
    })
  });
  if (!response.ok) throw new Error("无法拆分人物档案");
  return response.json();
}

/** 将后端媒体路径转换成浏览器可访问 URL。 */
export function mediaUrl(path: string | null | undefined): string {
  if (!path) return "";
  return `/media?path=${encodeURIComponent(path)}`;
}

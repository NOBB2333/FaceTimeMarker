import type { TrackDetectionItem, TrackItem, VideoDetail } from "../../api";

/** 绘制在人脸覆盖层上的绝对定位矩形。 */
export type FaceOverlayBox = {
  key: string;
  left: number;
  top: number;
  width: number;
  height: number;
  label: string;
};

/** 视频 object-contain 后真实可见内容在监视器中的位置。 */
type ContentRect = {
  left: number;
  top: number;
  width: number;
  height: number;
};

/** 当前时间附近可用于绘制的一条轨迹检测候选。 */
type FaceOverlayCandidate = {
  track: TrackItem;
  detection: TrackDetectionItem;
  bbox: [number, number, number, number];
  delta: number;
  area: number;
};

/** 构建覆盖层时需要的播放、可见性和命名上下文。 */
type BuildFaceOverlayOptions = {
  enabled: boolean;
  video: VideoDetail | null;
  contentRect: ContentRect | null;
  tracks: TrackItem[];
  detections: TrackDetectionItem[];
  currentTime: number;
  visiblePersonIds: Set<number>;
  highlightedTrack: TrackItem | null;
  personName: (personId: number) => string;
  toleranceSeconds: number;
};

/** 根据当前播放时间生成视频画面上的人脸框；没有逐帧匹配时回退到高亮轨迹代表框。 */
export function buildFaceOverlayBoxes(options: BuildFaceOverlayOptions): FaceOverlayBox[] {
  if (!options.enabled || !options.video || !options.contentRect) return [];
  const currentFrameCandidates = options.tracks
    .filter((track) => track.person_id === null || options.visiblePersonIds.has(track.person_id))
    .map((track) => {
      const frameMatch = nearestDetectionForTrack(
        track,
        options.detections,
        options.currentTime,
        options.toleranceSeconds,
      );
      if (!frameMatch.hasTrackDetections || !frameMatch.detection) return null;
      const bbox = parseBbox(frameMatch.detection.bbox_json);
      if (!bbox) return null;
      return {
        track,
        detection: frameMatch.detection,
        bbox,
        delta: frameMatch.delta,
        area: bboxArea(bbox),
      };
    })
    .filter((candidate): candidate is FaceOverlayCandidate => Boolean(candidate));
  const currentFrameBoxes = dedupeFaceOverlayCandidates(currentFrameCandidates)
    .map((candidate) => faceOverlayBoxFromTrack(candidate.track, candidate.bbox, options))
    .filter((box): box is FaceOverlayBox => Boolean(box));
  if (currentFrameBoxes.length > 0) return currentFrameBoxes;

  const fallbackBox = faceOverlayBoxFromTrack(
    options.highlightedTrack,
    parseBbox(options.highlightedTrack?.representative_bbox_json ?? "null"),
    options,
  );
  return fallbackBox ? [fallbackBox] : [];
}

/** 查找某条轨迹在当前播放时间附近最近的一次检测。 */
function nearestDetectionForTrack(
  track: TrackItem,
  detections: TrackDetectionItem[],
  currentTime: number,
  toleranceSeconds: number,
) {
  let hasTrackDetections = false;
  let best: TrackDetectionItem | null = null;
  let bestDelta = Number.POSITIVE_INFINITY;
  for (const detection of detections) {
    if (detection.track_id !== track.track_id) continue;
    hasTrackDetections = true;
    const delta = Math.abs(detection.timestamp - currentTime);
    if (delta < bestDelta) {
      best = detection;
      bestDelta = delta;
    }
  }
  return {
    detection: best && bestDelta <= toleranceSeconds ? best : null,
    hasTrackDetections,
    delta: bestDelta,
  };
}

/** 同一人物在同一帧可能有多条轨迹，保留最接近当前时间且质量更好的候选。 */
function dedupeFaceOverlayCandidates(candidates: FaceOverlayCandidate[]) {
  const bestByPerson = new Map<string, FaceOverlayCandidate>();
  for (const candidate of candidates) {
    const key =
      candidate.track.person_id === null
        ? `track:${candidate.track.track_id}`
        : `person:${candidate.track.person_id}`;
    const previous = bestByPerson.get(key);
    if (!previous || isBetterFaceOverlayCandidate(candidate, previous)) {
      bestByPerson.set(key, candidate);
    }
  }
  return [...bestByPerson.values()].sort((a, b) => {
    const aPerson = a.track.person_id ?? Number.MAX_SAFE_INTEGER;
    const bPerson = b.track.person_id ?? Number.MAX_SAFE_INTEGER;
    if (aPerson !== bPerson) return aPerson - bPerson;
    return a.track.track_id - b.track.track_id;
  });
}

/** 候选优先级：时间更近，其次置信度更高，最后使用面积更大的框。 */
function isBetterFaceOverlayCandidate(candidate: FaceOverlayCandidate, previous: FaceOverlayCandidate) {
  const deltaDiff = previous.delta - candidate.delta;
  if (Math.abs(deltaDiff) > 0.001) return deltaDiff > 0;
  const candidateConfidence = candidate.detection.confidence ?? 0;
  const previousConfidence = previous.detection.confidence ?? 0;
  if (candidateConfidence !== previousConfidence) {
    return candidateConfidence > previousConfidence;
  }
  return candidate.area > previous.area;
}

/** 计算 bbox 面积，异常反向坐标按 0 处理。 */
function bboxArea(bbox: [number, number, number, number]) {
  return Math.max(bbox[2] - bbox[0], 0) * Math.max(bbox[3] - bbox[1], 0);
}

/** 安全解析后端存储的人脸框 JSON。 */
function parseBbox(raw: string) {
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed) || parsed.length !== 4) return null;
    const values = parsed.map((value) => Number(value));
    if (values.some((value) => !Number.isFinite(value))) return null;
    return values as [number, number, number, number];
  } catch {
    return null;
  }
}

/** 将视频像素坐标转换到监视器中真实视频内容区域的 CSS 像素坐标。 */
function faceOverlayBoxFromTrack(
  track: TrackItem | null,
  bbox: [number, number, number, number] | null,
  options: BuildFaceOverlayOptions,
): FaceOverlayBox | null {
  const video = options.video;
  const rect = options.contentRect;
  if (!track || !video || !rect || !bbox) return null;
  const frameWidth = video.width;
  const frameHeight = video.height;
  if (frameWidth <= 0 || frameHeight <= 0) return null;

  const [x1, y1, x2, y2] = bbox;
  const safeX1 = clamp(x1, 0, frameWidth);
  const safeY1 = clamp(y1, 0, frameHeight);
  const safeX2 = clamp(x2, 0, frameWidth);
  const safeY2 = clamp(y2, 0, frameHeight);
  if (safeX2 <= safeX1 || safeY2 <= safeY1) return null;

  return {
    key: `${track.track_id}-${track.person_id ?? "none"}`,
    left: rect.left + (safeX1 / frameWidth) * rect.width,
    top: rect.top + (safeY1 / frameHeight) * rect.height,
    width: ((safeX2 - safeX1) / frameWidth) * rect.width,
    height: ((safeY2 - safeY1) / frameHeight) * rect.height,
    label: `${options.personName(track.person_id ?? -1)} / Track ${track.track_id}`,
  };
}

/** 限制 bbox 坐标不超过原视频尺寸。 */
function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

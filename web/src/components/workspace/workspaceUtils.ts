const countFormatter = new Intl.NumberFormat("zh-CN");

type VideoTitleSource = {
  title?: string | null;
  original_filename?: string | null;
  source_path?: string | null;
  path: string;
};

type GlobalPersonLabelSource = {
  global_person_id: string;
  label?: string | null;
  observation_count: number;
  four_view_asset_count: number;
};

export const supportedVideoExtensions = [".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"] as const;

/** 将数值限制在指定范围内。 */
export function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

/** 格式化工作台中的数量。 */
export function formatCount(value: number) {
  return countFormatter.format(value);
}

/** 格式化工作台中的时间。 */
export function formatTime(seconds: number) {
  const safe = Math.max(seconds, 0);
  const hours = Math.floor(safe / 3600);
  const minutes = Math.floor((safe % 3600) / 60);
  const secs = Math.floor(safe % 60);
  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  }
  return `${minutes}:${secs.toString().padStart(2, "0")}`;
}

/** 格式化工作台中的时长。 */
export function formatDuration(seconds: number) {
  return formatTime(seconds);
}

/** 判断文件名是否是支持的视频格式。 */
export function isSupportedVideo(fileName: string) {
  return supportedVideoExtensions.some((extension) => fileName.toLowerCase().endsWith(extension));
}

/** 从文本框中解析一个或多个后端本地视频路径。 */
export function parseServerVideoPaths(raw: string) {
  const seen = new Set<string>();
  const paths: string[] = [];
  for (const item of raw.replace(/\n/g, ";").split(";")) {
    const path = item.trim().replace(/^['"]|['"]$/g, "");
    if (!path || seen.has(path)) continue;
    seen.add(path);
    paths.push(path);
  }
  return paths;
}

/** 优先用作品元数据生成视频标题。 */
export function videoDisplayTitle(video: VideoTitleSource | null | undefined) {
  if (!video) return "";
  const title = meaningfulTitle(video.title);
  if (title) return title;
  if (video.original_filename) return stripExtension(video.original_filename);
  if (video.source_path) return stripExtension(video.source_path);
  return stripExtension(video.path);
}

/** 从完整路径中提取来源目录。 */
export function sourceDirectoryFromPath(path: string) {
  return path.replace(/[\\/][^\\/]*$/, "");
}

/** 生成人物档案下拉项的展示标签。 */
export function globalPersonLabel(person: GlobalPersonLabelSource) {
  const label = person.label?.trim() || person.global_person_id;
  return `${label} / ${formatCount(person.observation_count)} 次观测 / ${formatCount(person.four_view_asset_count)} 四视图`;
}

/** 从后端 JSON 字段解析轨迹 ID 列表。 */
export function parseTrackIds(raw: string) {
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      return parsed.map((value) => Number(value)).filter((value) => Number.isFinite(value));
    }
  } catch {
    return [];
  }
  return [];
}

/** 过滤空标题和纯哈希文件名。 */
function meaningfulTitle(value: string | null | undefined) {
  const text = value?.trim();
  if (!text) return "";
  const stem = stripExtension(text);
  if (/^(?:[0-9a-f]{16,}|[0-9a-f-]{24,})$/i.test(stem)) return "";
  return stem;
}

/** 去掉路径或文件名中的扩展名。 */
function stripExtension(value: string) {
  const name = value.split(/[\\/]/).filter(Boolean).at(-1) ?? value;
  return name.replace(/\.[^.]+$/, "");
}

/** 等待指定毫秒数。 */
export function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

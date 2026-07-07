<template>
  <div
    v-if="candidates.length === 0"
    class="border border-dashed border-white/10 bg-[#090d12] px-3 py-8 text-center text-xs text-[#697586]"
  >
    暂无可用截图
  </div>
  <div
    v-else
    class="grid gap-2"
    :class="displayMode === 'face' ? 'grid-cols-2 sm:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6' : 'sm:grid-cols-2 2xl:grid-cols-3'"
  >
    <button
      v-for="candidate in candidates"
      :key="candidate.id"
      class="group min-w-0 overflow-hidden border border-white/10 bg-[#090d12] text-left transition-colors duration-150 hover:border-[#34d5c8]/55 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]"
      :class="selectedIds.includes(candidate.id) ? 'border-[#f5c451] bg-[#171409]' : ''"
      type="button"
      @click="$emit('toggle', candidate)"
      @mouseenter="$emit('preview', candidate)"
    >
      <span
        class="relative block overflow-hidden bg-[#05070a]"
        :class="displayMode === 'face' ? 'aspect-square' : ''"
        :style="frameAspectStyle(candidate)"
      >
        <img
          v-if="tileImageUrl(candidate)"
          class="h-full w-full object-cover"
          :src="tileImageUrl(candidate)"
          alt=""
        />
        <span v-else class="grid h-full w-full place-items-center text-[#536171]">
          <Images class="h-6 w-6" aria-hidden="true" />
        </span>
        <span
          v-if="displayMode === 'marked' && faceBoxStyle(candidate)"
          class="pointer-events-none absolute border-2 border-[#ff3b30] shadow-[0_0_0_1px_rgba(0,0,0,0.65),0_0_14px_rgba(255,59,48,0.45)]"
          :style="faceBoxStyle(candidate)"
        />
        <span
          v-else-if="displayMode === 'marked'"
          class="absolute left-2 top-2 border border-[#ff8a8a]/35 bg-[#2a1214]/90 px-2 py-1 text-[11px] font-semibold text-[#ffb4b4]"
        >
          无框
        </span>
        <span
          v-if="selectedIds.includes(candidate.id)"
          class="absolute right-2 top-2 grid h-6 w-6 place-items-center border border-[#f5c451] bg-[#f5c451] text-[11px] font-bold text-[#11151b]"
        >
          ✓
        </span>
      </span>
      <span class="block border-t border-white/10 px-2.5 py-2">
        <span class="timecode block truncate text-[11px] text-[#34d5c8]">
          {{ candidate.timeLabel }}
        </span>
        <span class="mt-1 block truncate text-[11px] text-[#7d8998]">
          {{ candidate.subtitle }}
        </span>
      </span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { Images } from "@lucide/vue";

import { mediaUrl } from "../../api";

/** 参考帧网格的展示模式：完整帧、完整帧带框、仅脸部截图。 */
export type ReferenceDisplayMode = "frame" | "marked" | "face";

/** 从人物观测或作品人物轨迹转换来的前端参考帧候选。 */
export type ReferenceFrameCandidate = {
  /** 跨列表稳定的候选 ID，用于选择状态和 v-for key。 */
  id: string;
  label: string;
  subtitle: string;
  timeLabel: string;
  facePath: string | null;
  frameUrl: string | null;
  timestamp: number | null;
  frameIndex: number | null;
  personId: number | null;
  videoId: number | null;
  globalPersonId: string | null;
  /** 后端保存的人脸框 JSON，格式为 [x1, y1, x2, y2]。 */
  bboxJson: string | null;
  /** 原始视频尺寸用于把人脸框换算成百分比定位。 */
  videoWidth: number | null;
  videoHeight: number | null;
};

/** 网格只负责候选展示和选择态，候选来源与批量操作由父页面管理。 */
const props = defineProps<{
  candidates: ReferenceFrameCandidate[];
  selectedIds: string[];
  displayMode: ReferenceDisplayMode;
}>();

/** toggle 负责选择，preview 负责驱动右侧片段预览。 */
defineEmits<{
  toggle: [candidate: ReferenceFrameCandidate];
  preview: [candidate: ReferenceFrameCandidate];
}>();

/** 根据展示模式选择缩略图来源，完整帧缺失时回退到人脸截图。 */
function tileImageUrl(candidate: ReferenceFrameCandidate) {
  if (props.displayMode === "frame" || props.displayMode === "marked") {
    return candidate.frameUrl || mediaUrl(candidate.facePath);
  }
  return mediaUrl(candidate.facePath) || candidate.frameUrl || "";
}

/** 完整帧模式保持视频原始宽高比，脸部模式固定为方形网格。 */
function frameAspectStyle(candidate: ReferenceFrameCandidate) {
  if (props.displayMode === "face") return undefined;
  const width = candidate.videoWidth ?? 0;
  const height = candidate.videoHeight ?? 0;
  if (width <= 0 || height <= 0) return { aspectRatio: "16 / 9" };
  return { aspectRatio: `${width} / ${height}` };
}

/** 将后端像素坐标换算成覆盖在缩略图上的百分比定位。 */
function faceBoxStyle(candidate: ReferenceFrameCandidate) {
  if (props.displayMode !== "marked") return null;
  const bbox = parseBbox(candidate.bboxJson);
  const width = candidate.videoWidth ?? 0;
  const height = candidate.videoHeight ?? 0;
  if (!bbox || width <= 0 || height <= 0) return null;
  const [x1, y1, x2, y2] = bbox;
  const safeX1 = clamp(x1, 0, width);
  const safeY1 = clamp(y1, 0, height);
  const safeX2 = clamp(x2, 0, width);
  const safeY2 = clamp(y2, 0, height);
  if (safeX2 <= safeX1 || safeY2 <= safeY1) return null;
  return {
    left: `${(safeX1 / width) * 100}%`,
    top: `${(safeY1 / height) * 100}%`,
    width: `${((safeX2 - safeX1) / width) * 100}%`,
    height: `${((safeY2 - safeY1) / height) * 100}%`,
  };
}

/** 安全解析人脸框，坏数据直接隐藏标记而不是让组件报错。 */
function parseBbox(raw: string | null) {
  if (!raw) return null;
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

/** 防止异常 bbox 超出原始视频尺寸导致标记溢出缩略图。 */
function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}
</script>

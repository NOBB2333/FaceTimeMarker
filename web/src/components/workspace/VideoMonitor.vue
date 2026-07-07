<template>
  <section class="viewer-panel flex min-h-0 flex-col border-b border-white/10">
    <div class="flex h-11 items-center justify-between border-b border-white/10 bg-[#0f1319] px-4">
      <div class="flex min-w-0 items-center gap-3">
        <span class="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#697586]">Monitor</span>
        <span class="h-4 w-px bg-white/10" aria-hidden="true" />
        <span class="truncate text-sm font-semibold text-[#eef2f7]">
          {{ selectedVideo?.title ?? "未选择视频" }}
        </span>
      </div>
      <div class="hidden items-center gap-4 text-xs text-[#7d8998] sm:flex">
        <span v-if="selectedVideo">{{ selectedVideo.width }} x {{ selectedVideo.height }}</span>
        <span v-if="selectedVideo" class="timecode">{{ formatFps(selectedVideo.fps) }} FPS</span>
      </div>
    </div>

    <div
      ref="videoStageEl"
      class="video-stage relative grid min-h-0 flex-1 place-items-center overflow-hidden bg-black"
      :class="selectedVideo && selectedVideo.height > selectedVideo.width ? 'is-portrait' : ''"
    >
      <button
        v-if="selectedVideo"
        class="absolute right-3 top-3 z-20 inline-flex h-9 items-center justify-center gap-2 border border-white/10 bg-black/50 px-3 text-xs font-semibold text-[#cbd5e1] transition-colors duration-150 hover:border-[#34d5c8]/60 hover:text-[#34d5c8] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]"
        :class="faceBoxEnabled ? 'border-[#ff5a5a]/60 text-[#ffb4b4]' : ''"
        type="button"
        :aria-pressed="faceBoxEnabled"
        @click="$emit('toggleFaceBox')"
      >
        <ScanFace class="h-4 w-4" aria-hidden="true" />
        {{ faceBoxEnabled ? "框选开" : "框选关" }}
      </button>
      <video
        v-if="selectedVideo"
        ref="videoEl"
        class="viewer-video h-full max-h-full w-full max-w-full object-contain"
        controls
        :src="mediaUrl(selectedVideo.path)"
        @loadedmetadata="$emit('contentChanged')"
        @pause="$emit('playingChanged', false)"
        @play="$emit('playingChanged', true)"
        @seeked="$emit('contentChanged')"
        @timeupdate="emitTimeUpdate"
      />
      <div
        v-for="box in faceOverlayBoxes"
        :key="box.key"
        class="face-overlay pointer-events-none absolute z-10 border-2 border-[#ff4d4d] shadow-[0_0_0_1px_rgba(0,0,0,0.75),0_0_22px_rgba(255,77,77,0.35)]"
        :style="faceOverlayStyle(box)"
        aria-hidden="true"
      >
        <span class="absolute -top-6 left-0 max-w-[220px] truncate bg-[#ff4d4d] px-2 py-1 text-[11px] font-bold text-white shadow-[0_0_0_1px_rgba(0,0,0,0.45)]">
          {{ box.label }}
        </span>
      </div>
      <div v-if="!selectedVideo" class="grid h-full w-full place-items-center bg-[#07090c]">
        <div class="grid place-items-center gap-4 text-center">
          <div class="grid h-16 w-16 place-items-center border border-white/10 bg-[#111821] text-[#536171]">
            <Film class="h-8 w-8" aria-hidden="true" />
          </div>
          <div>
            <div class="text-sm font-semibold text-[#cbd5e1]">等待素材</div>
            <div class="mt-1 text-xs text-[#697586]">{{ statusMessage || "选择左侧视频" }}</div>
          </div>
        </div>
      </div>
    </div>

    <div class="flex h-14 items-center justify-between gap-3 border-t border-white/10 bg-[#0f1319] px-4">
      <div class="flex min-w-0 items-center gap-3">
        <button
          :aria-label="isPlaying ? '暂停视频' : '播放视频'"
          class="grid h-9 w-9 shrink-0 place-items-center bg-[#f5c451] text-[#11151b] transition-colors duration-150 hover:bg-[#ffd878] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#f5c451]"
          type="button"
          :disabled="!selectedVideo"
          @click="togglePlayback"
        >
          <Pause v-if="isPlaying" class="h-4 w-4" aria-hidden="true" />
          <Play v-else class="h-4 w-4" aria-hidden="true" />
        </button>
        <div class="timecode min-w-[78px] text-sm font-semibold text-[#f8fafc]">
          {{ formatTime(currentTime) }}
        </div>
        <div class="min-w-0 truncate text-sm text-[#8f9bac]">
          {{ selectedPersonLabel }} / {{ activeSegmentLabel }}
        </div>
      </div>
      <div class="hidden items-center gap-4 text-xs text-[#7d8998] md:flex">
        <span>{{ formatCount(peopleCount) }} 人物</span>
        <span>{{ formatCount(segmentsCount) }} 片段</span>
        <span>{{ formatCount(tracksCount) }} 轨迹</span>
        <span class="timecode">总长 {{ formatTime(selectedVideo?.duration_seconds ?? 0) }}</span>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { Film, Pause, Play, ScanFace } from "@lucide/vue";
import { ref } from "vue";

import { mediaUrl, type VideoItem } from "../../api";
import type { FaceOverlayBox } from "./faceOverlay";
import { formatCount, formatTime } from "./workspaceUtils";

/** 视频监视器接收的素材、播放和覆盖层状态。 */
const props = defineProps<{
  selectedVideo: VideoItem | null;
  faceBoxEnabled: boolean;
  faceOverlayBoxes: FaceOverlayBox[];
  isPlaying: boolean;
  currentTime: number;
  selectedPersonLabel: string;
  activeSegmentLabel: string;
  peopleCount: number;
  segmentsCount: number;
  tracksCount: number;
  statusMessage: string;
}>();

/** 视频监视器向工作台同步播放、定位和错误事件。 */
const emit = defineEmits<{
  toggleFaceBox: [];
  contentChanged: [];
  timeUpdate: [value: number];
  playingChanged: [value: boolean];
  playbackError: [message: string];
}>();

/** 底层 HTML 视频元素引用。 */
const videoEl = ref<HTMLVideoElement | null>(null);
/** 用于测量视频内容区域的舞台元素引用。 */
const videoStageEl = ref<HTMLElement | null>(null);
const fpsFormatter = new Intl.NumberFormat("zh-CN", {
  maximumFractionDigits: 1,
  minimumFractionDigits: 0
});

/** 将人脸框数据转换为绝对定位样式。 */
function faceOverlayStyle(box: FaceOverlayBox) {
  return {
    left: `${box.left}px`,
    top: `${box.top}px`,
    width: `${box.width}px`,
    height: `${box.height}px`,
  };
}

/** 将 video timeupdate 事件同步给父组件。 */
function emitTimeUpdate(event: Event) {
  emit("timeUpdate", (event.currentTarget as HTMLVideoElement).currentTime);
}

/** 定位到指定秒数并暂停视频。 */
async function seekAndPause(seconds: number) {
  if (!videoEl.value) return false;
  videoEl.value.currentTime = seconds;
  videoEl.value.pause();
  emit("contentChanged");
  return true;
}

/** 定位到指定秒数并尝试播放视频。 */
async function seekAndPlay(seconds: number) {
  if (!videoEl.value) return false;
  videoEl.value.currentTime = seconds;
  emit("contentChanged");
  try {
    await videoEl.value.play();
    return true;
  } catch {
    emit("playbackError", "浏览器阻止了自动播放，请在视频窗口手动播放。");
    return false;
  }
}

/** 在播放和暂停之间切换当前视频。 */
async function togglePlayback() {
  if (!videoEl.value) return;
  if (videoEl.value.paused) {
    try {
      await videoEl.value.play();
    } catch {
      emit("playbackError", "浏览器阻止了播放，请检查视频文件是否可访问。");
    }
  } else {
    videoEl.value.pause();
  }
}

/** 测量 object-contain 后真实可见的视频内容区域。 */
function measureContentRect() {
  const stage = videoStageEl.value;
  const video = videoEl.value;
  const selected = props.selectedVideo;
  if (!stage || !video || !selected) return null;

  const stageRect = stage.getBoundingClientRect();
  const videoRect = video.getBoundingClientRect();
  const frameWidth = video.videoWidth || selected.width;
  const frameHeight = video.videoHeight || selected.height;
  if (frameWidth <= 0 || frameHeight <= 0 || videoRect.width <= 0 || videoRect.height <= 0) {
    return null;
  }

  const scale = Math.min(videoRect.width / frameWidth, videoRect.height / frameHeight);
  const contentWidth = frameWidth * scale;
  const contentHeight = frameHeight * scale;
  return {
    left: videoRect.left - stageRect.left + (videoRect.width - contentWidth) / 2,
    top: videoRect.top - stageRect.top + (videoRect.height - contentHeight) / 2,
    width: contentWidth,
    height: contentHeight,
  };
}

/** 格式化视频帧率显示。 */
function formatFps(value: number) {
  return fpsFormatter.format(value);
}

/** 暴露给工作台调用的播放和测量方法。 */
defineExpose({
  measureContentRect,
  seekAndPause,
  seekAndPlay,
  togglePlayback,
});
</script>

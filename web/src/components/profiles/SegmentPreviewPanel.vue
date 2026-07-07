<template>
  <section class="sticky top-0 z-30 border-b border-white/10 bg-[#0f1319] px-4 py-3">
    <div class="flex items-center justify-between gap-3">
      <h3 class="text-sm font-semibold text-[#f8fafc]">人物片段预览</h3>
      <span class="timecode text-xs text-[#7d8998]">{{ meta }}</span>
    </div>
    <div class="mt-3 border border-white/10 bg-[#090d12]">
      <video
        v-if="work"
        ref="videoEl"
        class="aspect-video w-full bg-black object-contain"
        controls
        muted
        playsinline
        :src="mediaUrl(work.path)"
        @loadedmetadata="emit('loadedMetadata')"
      />
      <span v-else class="grid aspect-video w-full place-items-center bg-[#090d12] text-[#536171]">
        <Film class="h-8 w-8" aria-hidden="true" />
      </span>
      <div class="border-t border-white/10 px-3 py-2">
        <p class="truncate text-xs font-semibold text-[#f8fafc]">{{ title }}</p>
        <p class="mt-1 truncate text-[11px] text-[#7d8998]">
          {{ loading ? "正在读取片段" : error || "悬停人物卡片可预览片段" }}
        </p>
      </div>
    </div>
    <div class="mt-3 grid grid-cols-3 gap-2">
      <button
        class="inline-flex h-9 items-center justify-center gap-1 border border-white/10 bg-[#151b23] text-xs font-semibold text-[#cbd5e1] transition-colors duration-150 hover:border-[#34d5c8]/60 hover:text-[#34d5c8] disabled:opacity-40"
        type="button"
        :disabled="!canStep"
        @click="emit('step', -1)"
      >
        <ChevronLeft class="h-4 w-4" aria-hidden="true" />
        上一段
      </button>
      <button
        class="inline-flex h-9 items-center justify-center gap-1 bg-[#f5c451] text-xs font-semibold text-[#11151b] transition-colors duration-150 hover:bg-[#ffd878] disabled:opacity-40"
        type="button"
        :disabled="!canPlay"
        @click="emit('play')"
      >
        <Play class="h-4 w-4" aria-hidden="true" />
        播放
      </button>
      <button
        class="inline-flex h-9 items-center justify-center gap-1 border border-white/10 bg-[#151b23] text-xs font-semibold text-[#cbd5e1] transition-colors duration-150 hover:border-[#34d5c8]/60 hover:text-[#34d5c8] disabled:opacity-40"
        type="button"
        :disabled="!canStep"
        @click="emit('step', 1)"
      >
        下一段
        <ChevronRight class="h-4 w-4" aria-hidden="true" />
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ChevronLeft, ChevronRight, Film, Play } from "@lucide/vue";
import { ref } from "vue";

import { mediaUrl, type VideoDetail } from "../../api";

/** 档案页右侧的人物片段预览状态，由父页面根据悬停候选帧同步。 */
defineProps<{
  work: VideoDetail | null;
  meta: string;
  title: string;
  loading: boolean;
  error: string;
  canStep: boolean;
  canPlay: boolean;
}>();

/** 片段切换和播放控制交给父页面，组件只暴露 video 元素供父级定位时间。 */
const emit = defineEmits<{
  step: [delta: number];
  play: [];
  loadedMetadata: [];
}>();

/** 内部 video 引用会通过 defineExpose 暴露给父页面做精确 seek/play。 */
const videoEl = ref<HTMLVideoElement | null>(null);

defineExpose({
  getVideoElement: () => videoEl.value,
});
</script>

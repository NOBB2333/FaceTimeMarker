<template>
  <div class="sr-only" aria-live="polite">{{ statusMessage }}</div>
  <div
    v-if="statusMessage && !errorMessage"
    class="fixed bottom-4 left-1/2 z-50 max-w-[calc(100vw-32px)] -translate-x-1/2 border border-white/10 bg-[#11151b] px-4 py-3 text-sm text-[#cbd5e1] shadow-2xl shadow-black/40"
  >
    {{ statusMessage }}
  </div>
  <div
    v-if="errorMessage"
    class="fixed bottom-4 left-1/2 z-50 max-w-[calc(100vw-32px)] -translate-x-1/2 border border-[#7f2e2e] bg-[#2a1215] px-4 py-3 text-sm text-[#fecaca] shadow-2xl shadow-black/40"
  >
    {{ errorMessage }}
  </div>
  <div
    v-if="reviewDragPreview"
    class="review-drag-preview pointer-events-none fixed z-[70]"
    :style="reviewDragPreviewStyle"
    aria-hidden="true"
  >
    <div class="flex items-center gap-3 border border-[#34d5c8]/50 bg-[#0a0d12]/95 p-2 shadow-2xl shadow-black/45">
      <span class="relative block h-14 w-14 overflow-hidden bg-[#151b23]">
        <img
          v-if="reviewDragPreview.facePath"
          class="h-full w-full object-cover"
          :src="mediaUrl(reviewDragPreview.facePath)"
          alt=""
          draggable="false"
        />
        <span v-else class="grid h-full w-full place-items-center text-[#697586]">
          <Image class="h-6 w-6" aria-hidden="true" />
        </span>
      </span>
      <span class="min-w-0">
        <span class="block text-xs font-semibold text-[#f8fafc]">
          {{ formatCount(reviewDragPreview.count) }} 张人脸
        </span>
        <span class="mt-1 block text-[11px] text-[#34d5c8]">拖到人物清单归类</span>
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Image } from "@lucide/vue";
import type { StyleValue } from "vue";

import { mediaUrl } from "../../api";

/** 审阅区拖拽代表脸时跟随指针显示的浮层信息。 */
type ReviewDragPreview = {
  x: number;
  y: number;
  count: number;
  facePath: string | null;
};

/** 工作台全局反馈层，集中展示状态、错误和拖拽预览，不参与业务状态修改。 */
defineProps<{
  statusMessage: string;
  errorMessage: string;
  reviewDragPreview: ReviewDragPreview | null;
  reviewDragPreviewStyle: StyleValue;
  formatCount: (value: number) => string;
}>();
</script>

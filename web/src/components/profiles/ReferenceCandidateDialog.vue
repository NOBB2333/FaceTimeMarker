<template>
  <div
    v-if="candidate"
    class="fixed inset-0 z-50 grid place-items-center bg-black/75 p-6"
    role="dialog"
    aria-modal="true"
    @click.self="emit('close')"
  >
    <div class="max-h-full w-full max-w-5xl overflow-hidden border border-white/10 bg-[#0d1117] shadow-2xl">
      <div class="flex items-center justify-between gap-3 border-b border-white/10 px-4 py-3">
        <div class="min-w-0">
          <h3 class="truncate text-sm font-semibold text-[#f8fafc]">{{ candidate.label }}</h3>
          <p class="mt-1 text-xs text-[#7d8998]">{{ candidate.timeLabel }}</p>
        </div>
        <button
          class="grid h-8 w-8 shrink-0 place-items-center border border-white/10 bg-[#151b23] text-[#cbd5e1] transition-colors duration-150 hover:border-[#34d5c8]/60 hover:text-[#34d5c8] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]"
          type="button"
          aria-label="关闭参考素材预览"
          @click="emit('close')"
        >
          <X class="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
      <div class="max-h-[calc(100vh-132px)] overflow-auto bg-[#05070a] p-4">
        <img
          v-if="fullFrameUrl(candidate)"
          class="mx-auto max-h-[calc(100vh-164px)] max-w-full object-contain"
          :src="fullFrameUrl(candidate)"
          :alt="candidate.label"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { X } from "@lucide/vue";

import { mediaUrl } from "../../api";
import type { ReferenceFrameCandidate } from "./ReferenceFrameGrid.vue";

/** 参考素材预览弹窗接收当前候选帧；为空时不渲染弹层。 */
defineProps<{
  candidate: ReferenceFrameCandidate | null;
}>();

/** 弹窗关闭由父组件清空当前预览候选。 */
const emit = defineEmits<{
  close: [];
}>();

/** 大图优先展示完整视频帧，缺失时回退到人脸截图。 */
function fullFrameUrl(candidate: ReferenceFrameCandidate | null) {
  if (!candidate) return "";
  return candidate.frameUrl || mediaUrl(candidate.facePath);
}
</script>

<template>
  <section class="border-b border-white/10 px-4 py-3">
    <div class="flex items-center justify-between gap-3">
      <h3 class="text-sm font-semibold text-[#f8fafc]">参考素材</h3>
      <span class="text-xs text-[#7d8998]">{{ formatCount(selectedCount) }} 已选</span>
    </div>
    <div
      v-if="candidates.length === 0"
      class="mt-3 border border-dashed border-white/10 bg-[#090d12] px-3 py-10 text-center text-xs text-[#697586]"
    >
      {{ emptyLabel }}
    </div>
    <div v-else class="mt-3 space-y-3">
      <button
        v-for="candidate in candidates"
        :key="candidate.id"
        class="block w-full overflow-hidden border border-white/10 bg-[#0a0e13] text-left transition-colors duration-150 hover:border-[#34d5c8]/60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]"
        type="button"
        @click="emit('open', candidate)"
      >
        <img
          v-if="fullFrameUrl(candidate)"
          class="aspect-video w-full object-cover"
          :src="fullFrameUrl(candidate)"
          alt=""
        />
        <span v-else class="grid aspect-video w-full place-items-center bg-[#090d12] text-[#536171]">
          <Images class="h-8 w-8" aria-hidden="true" />
        </span>
        <span class="block border-t border-white/10 px-3 py-2">
          <span class="truncate text-xs font-semibold text-[#f8fafc]">{{ candidate.label }}</span>
          <span class="mt-1 block truncate text-[11px] text-[#7d8998]">{{ candidate.timeLabel }}</span>
        </span>
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { Images } from "@lucide/vue";

import { mediaUrl } from "../../api";
import type { ReferenceFrameCandidate } from "./ReferenceFrameGrid.vue";

/** 右侧栏中的已选参考素材缩略列表。 */
withDefaults(
  defineProps<{
    candidates: ReferenceFrameCandidate[];
    selectedCount: number;
    emptyLabel?: string;
  }>(),
  {
    emptyLabel: "从左侧人物镜头中选择参考帧",
  },
);

/** 点击缩略图后由父页面打开大图预览。 */
const emit = defineEmits<{
  open: [candidate: ReferenceFrameCandidate];
}>();

const numberFormatter = new Intl.NumberFormat("zh-CN");

/** 格式化已选参考素材数量。 */
function formatCount(value: number) {
  return numberFormatter.format(value);
}

/** 右侧栏优先展示完整视频帧，缺失时回退到人脸截图。 */
function fullFrameUrl(candidate: ReferenceFrameCandidate) {
  return candidate.frameUrl || mediaUrl(candidate.facePath);
}
</script>

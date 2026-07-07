<template>
  <header class="topbar flex h-[60px] items-center justify-between border-b border-white/10 bg-[#11151b]/95 px-4">
    <div class="flex min-w-0 items-center gap-3">
      <div class="grid h-9 w-9 shrink-0 place-items-center border border-[#34d5c8]/40 bg-[#34d5c8]/10 text-[#34d5c8]">
        <Film class="h-5 w-5" aria-hidden="true" />
      </div>
      <div class="min-w-0">
        <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8f9bac]" translate="no">
          FaceTimeMarker
        </p>
        <h1 class="truncate text-[15px] font-semibold text-[#f8fafc]">人物识别时间轴工作台</h1>
      </div>
    </div>

    <div class="flex min-w-0 items-center gap-3">
      <div class="hidden items-center gap-4 border border-white/10 bg-[#0d1117] px-3 py-2 text-xs text-[#8f9bac] lg:flex">
        <span>{{ formatCount(videosCount) }} 视频</span>
        <span>{{ formatCount(peopleCount) }} 人物</span>
        <span>{{ formatCount(segmentsCount) }} 片段</span>
        <span class="timecode text-[#f5c451]">{{ formatTime(currentTime) }}</span>
      </div>

      <div class="flex items-center border border-white/10 bg-[#0d1117] p-1">
        <button
          v-for="preset in presets"
          :key="preset.id"
          class="h-8 px-3 text-xs font-semibold text-[#8f9bac] transition-colors duration-150 hover:text-[#f8fafc] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]"
          :class="selectedPreset === preset.id ? 'bg-[#22313a] text-[#34d5c8]' : ''"
          type="button"
          @click="$emit('update:selectedPreset', preset.id)"
        >
          {{ preset.label }}
        </button>
      </div>

      <button
        aria-label="刷新视频列表"
        class="grid h-10 w-10 place-items-center border border-white/10 bg-[#151b23] text-[#cbd5e1] transition-colors duration-150 hover:border-[#34d5c8]/60 hover:text-[#34d5c8] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]"
        type="button"
        @click="$emit('refresh')"
      >
        <RefreshCw class="h-4 w-4" aria-hidden="true" />
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { Film, RefreshCw } from "@lucide/vue";

import { formatCount, formatTime } from "./workspaceUtils";

/** 分析预设按钮的展示模型。 */
type PresetOption = {
  id: string;
  label: string;
};

/** 工作台顶部栏展示的统计和预设状态。 */
defineProps<{
  videosCount: number;
  peopleCount: number;
  segmentsCount: number;
  currentTime: number;
  presets: PresetOption[];
  selectedPreset: string;
}>();

/** 工作台顶部栏向父级同步预设切换和刷新动作。 */
defineEmits<{
  "update:selectedPreset": [value: string];
  refresh: [];
}>();

</script>

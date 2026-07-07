<template>
  <div class="flex items-center border border-white/10 bg-[#0a0d12] p-1">
    <button
      v-for="mode in modes"
      :key="mode.value"
      class="h-8 px-3 text-xs font-semibold transition-colors duration-150"
      :class="modelValue === mode.value ? 'bg-[#22313a] text-[#34d5c8]' : 'text-[#8f9bac] hover:text-[#f8fafc]'"
      type="button"
      @click="emit('update:modelValue', mode.value)"
    >
      {{ mode.label }}
    </button>
  </div>
</template>

<script setup lang="ts">
import type { ReferenceDisplayMode } from "./ReferenceFrameGrid.vue";

/** 当前参考素材展示模式，使用 v-model 与父页面同步。 */
defineProps<{
  modelValue: ReferenceDisplayMode;
}>();

/** 切换展示模式时保持标准 v-model 事件名。 */
const emit = defineEmits<{
  "update:modelValue": [mode: ReferenceDisplayMode];
}>();

/** 展示模式固定为三档，避免父页面和网格组件各自维护文案。 */
const modes: Array<{ value: ReferenceDisplayMode; label: string }> = [
  { value: "frame", label: "完整画面" },
  { value: "marked", label: "脸部标记" },
  { value: "face", label: "脸部截图" },
];
</script>

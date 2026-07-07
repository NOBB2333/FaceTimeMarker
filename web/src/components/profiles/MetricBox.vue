<template>
  <div class="border border-white/10 bg-[#0a0e13] px-3 py-2">
    <div class="text-[11px] text-[#697586]">{{ label }}</div>
    <div class="timecode mt-1 text-sm font-semibold text-[#f8fafc]">{{ value }}</div>
  </div>
</template>

<script setup lang="ts">
/** 档案详情顶部的紧凑指标块，父组件负责提前格式化展示值。 */
defineProps<{
  label: string;
  value: string;
}>();
</script>

<template>
  <div
    v-if="previewAsset"
    class="fixed inset-0 z-50 grid place-items-center bg-black/75 p-6"
    role="dialog"
    aria-modal="true"
    @click.self="emit('close')"
  >
    <div class="max-h-full w-full max-w-5xl overflow-hidden border border-white/10 bg-[#0d1117] shadow-2xl">
      <div class="flex items-center justify-between gap-3 border-b border-white/10 px-4 py-3">
        <div class="min-w-0">
          <h3 class="truncate text-sm font-semibold text-[#f8fafc]">{{ previewAsset.label }}</h3>
          <p class="mt-1 text-xs text-[#7d8998]">
            四视图原图
            <span v-if="hasMultipleAssets" class="timecode ml-2 text-[#f5c451]">
              {{ displayAssetIndex }} / {{ assetCount }}
            </span>
          </p>
        </div>
        <div class="flex shrink-0 items-center gap-2">
          <button
            v-if="hasMultipleAssets"
            class="grid h-8 w-8 place-items-center border border-white/10 bg-[#151b23] text-[#cbd5e1] transition-colors duration-150 hover:border-[#f5c451]/60 hover:text-[#f5c451] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#f5c451]"
            type="button"
            aria-label="上一张四视图资产"
            @click="emit('previous')"
          >
            <ChevronLeft class="h-4 w-4" aria-hidden="true" />
          </button>
          <button
            v-if="hasMultipleAssets"
            class="grid h-8 w-8 place-items-center border border-white/10 bg-[#151b23] text-[#cbd5e1] transition-colors duration-150 hover:border-[#f5c451]/60 hover:text-[#f5c451] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#f5c451]"
            type="button"
            aria-label="下一张四视图资产"
            @click="emit('next')"
          >
            <ChevronRight class="h-4 w-4" aria-hidden="true" />
          </button>
          <button
            class="grid h-8 w-8 place-items-center border border-white/10 bg-[#151b23] text-[#cbd5e1] transition-colors duration-150 hover:border-[#34d5c8]/60 hover:text-[#34d5c8] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]"
            type="button"
            aria-label="关闭四视图原图预览"
            @click="emit('close')"
          >
            <X class="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      </div>
      <div class="max-h-[calc(100vh-132px)] overflow-auto bg-[#05070a] p-4">
        <img
          v-if="previewAsset.image_path"
          class="mx-auto max-h-[calc(100vh-164px)] max-w-full object-contain"
          :src="mediaUrl(previewAsset.image_path)"
          :alt="previewAsset.label"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ChevronLeft, ChevronRight, X } from "@lucide/vue";
import { computed, onBeforeUnmount, onMounted } from "vue";

import { mediaUrl, type FourViewAssetItem } from "../../api";

/** 预览弹窗接收当前未切分四视图原图；为空时不渲染弹层。 */
const props = withDefaults(
  defineProps<{
    asset: FourViewAssetItem | null;
    assetIndex?: number;
    assetCount?: number;
  }>(),
  {
    assetIndex: 0,
    assetCount: 0,
  },
);

/** 弹窗关闭由父组件清空当前预览资产。 */
const emit = defineEmits<{
  close: [];
  previous: [];
  next: [];
}>();

const previewAsset = computed(() => props.asset);
const hasMultipleAssets = computed(() => props.assetCount > 1);
const displayAssetIndex = computed(() => Math.min(props.assetIndex + 1, props.assetCount));

function handleKeydown(event: KeyboardEvent) {
  if (!props.asset) return;
  if (event.key === "Escape") {
    event.preventDefault();
    emit("close");
    return;
  }
  if (!hasMultipleAssets.value) return;
  if (event.key === "ArrowLeft") {
    event.preventDefault();
    emit("previous");
    return;
  }
  if (event.key === "ArrowRight") {
    event.preventDefault();
    emit("next");
  }
}

onMounted(() => {
  window.addEventListener("keydown", handleKeydown);
});

onBeforeUnmount(() => {
  window.removeEventListener("keydown", handleKeydown);
});
</script>

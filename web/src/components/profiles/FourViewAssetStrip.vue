<template>
  <div class="min-w-[220px] max-w-[360px] flex-1 basis-[300px]">
    <div class="mb-1 flex items-center justify-between gap-2 text-[11px]">
      <span class="font-semibold text-[#cbd5e1]">四视图资产</span>
      <span class="timecode text-[#8f9bac]">{{ formatCount(assets.length) }} 张</span>
    </div>
    <div class="flex max-w-full gap-2 overflow-x-auto pb-1">
      <template v-if="assets.length > 0">
        <div
          v-for="(asset, index) in assets"
          :key="asset.id"
          class="relative h-14 w-20 shrink-0 overflow-hidden border border-white/10 bg-[#090d12]"
        >
          <button
            class="h-full w-full transition-colors duration-150 hover:border-[#f5c451]/70 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#f5c451]"
            type="button"
            :title="asset.label"
            @click="emit('previewAsset', asset, index, assets)"
          >
            <img
              v-if="asset.image_path"
              class="h-full w-full object-cover"
              :src="mediaUrl(asset.image_path)"
              alt=""
            />
            <span v-else class="grid h-full w-full place-items-center text-[#697586]">
              <Images class="h-4 w-4" aria-hidden="true" />
            </span>
          </button>
          <button
            class="absolute right-1 top-1 grid h-6 w-6 place-items-center border border-[#ff8a8a]/40 bg-[#2a1214]/95 text-[#ffb4b4] transition-colors duration-150 hover:border-[#ff8a8a] hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#ff8a8a]"
            type="button"
            title="删除四视图资产"
            @click="emit('deleteAsset', asset)"
          >
            <Trash2 class="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        </div>
      </template>
      <div
        v-else
        class="grid h-14 w-20 shrink-0 place-items-center border border-dashed border-white/15 bg-[#090d12] text-[11px] text-[#697586]"
      >
        待生成
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Images, Trash2 } from "@lucide/vue";

import { mediaUrl, type FourViewAssetItem } from "../../api";

/** 紧凑四视图资产条，主要用于作品人物卡片顶部展示已生成资产。 */
withDefaults(
  defineProps<{
    assets?: FourViewAssetItem[];
  }>(),
  {
    assets: () => [],
  },
);

/** 预览和删除都由父页面处理，组件保持无状态。 */
const emit = defineEmits<{
  previewAsset: [asset: FourViewAssetItem, index?: number, assets?: FourViewAssetItem[]];
  deleteAsset: [asset: FourViewAssetItem];
}>();

const numberFormatter = new Intl.NumberFormat("zh-CN");

/** 格式化资产数量。 */
function formatCount(value: number) {
  return numberFormatter.format(value);
}
</script>

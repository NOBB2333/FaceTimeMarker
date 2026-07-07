<template>
  <div class="border border-white/10 bg-[#0a0e13] p-3">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <span class="flex items-center gap-2 text-sm font-semibold text-[#f8fafc]">
        <Sparkles class="h-4 w-4 text-[#f5c451]" aria-hidden="true" />
        {{ dense ? "四视图组" : "四视图资产" }}
      </span>
      <div class="flex flex-wrap items-center justify-end gap-2">
        <span class="border border-[#f5c451]/25 bg-[#2a2414] px-2 py-1 text-[11px] font-semibold text-[#f5c451]">
          {{ selectableCount > 0 ? `${selectionLabel} ${selectedCount} / ${selectableCount}` : `${selectedCount} 张参考` }}
        </span>
        <button
          v-if="canSelectAll"
          class="inline-flex h-8 shrink-0 items-center justify-center border border-white/10 bg-[#151b23] px-3 text-xs font-semibold text-[#cbd5e1] transition-colors duration-150 hover:border-[#34d5c8]/60 hover:text-[#34d5c8] disabled:opacity-40"
          type="button"
          :disabled="selectableCount === 0 || selectedCount >= selectableCount"
          @click="emit('selectAll')"
        >
          {{ selectedCount >= selectableCount && selectableCount > 0 ? "已全选" : selectAllLabel }}
        </button>
        <button
          v-if="selectedCount > 0"
          class="inline-flex h-8 shrink-0 items-center justify-center border border-white/10 bg-[#151b23] px-3 text-xs font-semibold text-[#8f9bac] transition-colors duration-150 hover:border-[#ff8a8a]/50 hover:text-[#ffb4b4]"
          type="button"
          @click="emit('clearSelection')"
        >
          清空
        </button>
        <button
          class="inline-flex h-8 shrink-0 items-center justify-center gap-2 px-3 text-xs font-semibold transition-colors duration-150 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#f5c451]"
          :class="selectedCount > 0 ? 'bg-[#f5c451] text-[#11151b] hover:bg-[#ffd878] disabled:cursor-wait disabled:opacity-60' : 'border border-white/10 bg-[#151b23] text-[#697586]'"
          type="button"
          :disabled="selectedCount === 0 || generating"
          @click="emit('generate')"
        >
          <Sparkles class="h-4 w-4" aria-hidden="true" />
          {{ generating ? "生成中" : selectedCount > 0 ? "生成四视图" : "先选参考素材" }}
        </button>
        <label
          v-if="canUpload"
          class="inline-flex h-8 shrink-0 items-center justify-center gap-2 border border-white/10 bg-[#151b23] px-3 text-xs font-semibold text-[#cbd5e1] transition-colors duration-150 hover:border-[#34d5c8]/60 hover:text-[#34d5c8]"
          :class="uploading ? 'cursor-wait opacity-60' : 'cursor-pointer'"
        >
          <Images class="h-4 w-4" aria-hidden="true" />
          {{ uploading ? "上传中" : "上传原图" }}
          <input
            class="sr-only"
            type="file"
            accept="image/png,image/jpeg,image/webp,image/avif"
            :disabled="uploading"
            @change="handleAssetFileChange"
          />
        </label>
      </div>
    </div>

    <div class="mt-3 flex gap-2 overflow-x-auto" :class="compact ? 'pb-0' : 'pb-1'">
      <template v-if="assets.length > 0">
        <div
          v-for="(asset, index) in assets"
          :key="asset.id"
          class="flex h-16 min-w-[260px] items-center gap-3 border border-white/10 bg-[#090d12] px-3 text-left"
        >
          <button
            class="flex min-w-0 flex-1 items-center gap-3 text-left transition-colors duration-150 hover:text-[#f5c451] disabled:cursor-default disabled:opacity-70 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#f5c451]"
            type="button"
            :disabled="!asset.image_path"
            @click="emit('previewAsset', asset, index, assets)"
          >
            <img
              v-if="asset.image_path"
              class="h-10 w-14 shrink-0 object-cover"
              :src="mediaUrl(asset.image_path)"
              alt=""
            />
            <div v-else class="grid h-10 w-14 shrink-0 place-items-center border border-white/10 bg-[#080a0d] text-[#697586]">
              <Images class="h-4 w-4" aria-hidden="true" />
            </div>
            <div class="min-w-0">
              <p class="truncate text-xs font-semibold text-[#f8fafc]">{{ asset.label }}</p>
              <p class="mt-1 truncate text-[11px] text-[#7d8998]">{{ asset.image_path ? "点击查看原图" : "待生成" }}</p>
            </div>
          </button>
          <button
            class="grid h-8 w-8 shrink-0 place-items-center border border-[#ff8a8a]/30 bg-[#2a1214] text-[#ffb4b4] transition-colors duration-150 hover:border-[#ff8a8a] hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#ff8a8a]"
            type="button"
            title="删除四视图资产"
            @click="emit('deleteAsset', asset)"
          >
            <Trash2 class="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      </template>

      <div v-else class="flex h-16 min-w-[220px] items-center gap-3 border border-dashed border-white/15 bg-[#090d12] px-3">
        <div class="grid h-10 w-14 shrink-0 grid-cols-2 overflow-hidden border border-white/10 bg-[#080a0d]">
          <span
            v-for="slot in viewSlots"
            :key="slot"
            class="grid place-items-center border border-white/10 text-[9px] text-[#697586]"
          >
            {{ slot }}
          </span>
        </div>
        <div class="min-w-0">
          <p class="truncate text-xs font-semibold text-[#cbd5e1]">预留 {{ formatCount(Math.max(setCount, 1)) }} 组资产</p>
          <p class="mt-1 truncate text-[11px] text-[#697586]">生成后显示未切分原图</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Images, Sparkles, Trash2 } from "@lucide/vue";

import { mediaUrl, type FourViewAssetItem } from "../../api";

/** 四视图生成/上传状态条，可在人物详情和作品人物列表中复用。 */
withDefaults(
  defineProps<{
    setCount?: number;
    selectedCount?: number;
    selectableCount?: number;
    assets?: FourViewAssetItem[];
    uploading?: boolean;
    generating?: boolean;
    canUpload?: boolean;
    canSelectAll?: boolean;
    selectAllLabel?: string;
    selectionLabel?: string;
    compact?: boolean;
    dense?: boolean;
  }>(),
  {
    setCount: 1,
    selectedCount: 0,
    selectableCount: 0,
    assets: () => [],
    uploading: false,
    generating: false,
    canUpload: false,
    canSelectAll: false,
    selectAllLabel: "全选参考",
    selectionLabel: "参考素材",
    compact: false,
    dense: false,
  },
);

/** 四视图相关的实际生成、上传、删除和预览都交给父页面调用 API。 */
const emit = defineEmits<{
  generate: [];
  previewAsset: [asset: FourViewAssetItem, index?: number, assets?: FourViewAssetItem[]];
  deleteAsset: [asset: FourViewAssetItem];
  uploadAsset: [file: File];
  selectAll: [];
  clearSelection: [];
}>();

const numberFormatter = new Intl.NumberFormat("zh-CN");

/** 空状态中用于提示四视图一组资产的四个占位。 */
const viewSlots = ["正", "侧", "背", "参考"];

/** 格式化四视图状态条里的数量。 */
function formatCount(value: number) {
  return numberFormatter.format(value);
}

/** 读取上传控件中的单张原图并重置 input，确保再次选择同一文件也能触发 change。 */
function handleAssetFileChange(event: Event) {
  const input = event.target as HTMLInputElement | null;
  const file = input?.files?.[0];
  if (file) {
    emit("uploadAsset", file);
  }
  if (input) input.value = "";
}
</script>

<template>
  <aside class="min-h-0 border-r border-white/10 bg-[#0f1319] p-4">
    <div class="space-y-1">
      <p class="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#697586]">Search</p>
      <h1 class="text-lg font-semibold text-[#f8fafc]">人物库搜索</h1>
      <p class="text-xs leading-5 text-[#7d8998]">
        搜索你重命名过的人物、全局人物 ID、视频标题或路径。
      </p>
    </div>

    <form class="mt-5 space-y-3" @submit.prevent="$emit('textSearch')">
      <label class="block">
        <span class="mb-1 block text-[11px] font-semibold uppercase tracking-[0.16em] text-[#697586]">
          Keyword
        </span>
        <input
          :value="query"
          class="h-10 w-full border border-white/10 bg-[#0a0d12] px-3 text-sm text-[#eef2f7] placeholder:text-[#536171] focus-visible:border-[#34d5c8] focus-visible:outline-none"
          placeholder="人物备注 / 视频名 / global_person_000001"
          @input="$emit('update:query', ($event.target as HTMLInputElement).value)"
        />
      </label>
      <button
        class="inline-flex h-10 w-full items-center justify-center gap-2 bg-[#34d5c8] px-4 text-sm font-semibold text-[#061012] transition-colors duration-150 hover:bg-[#59eee2] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]"
        type="submit"
        :disabled="isSearchingText"
      >
        <Search class="h-4 w-4" aria-hidden="true" />
        {{ isSearchingText ? "搜索中" : "搜索人物" }}
      </button>
    </form>

    <div class="mt-6 border-t border-white/10 pt-5">
      <p class="text-sm font-semibold text-[#f8fafc]">以图搜图</p>
      <p class="mt-1 text-xs leading-5 text-[#7d8998]">
        上传一张清晰人脸图，匹配全局人物库里的代表 embedding。
      </p>
      <label class="mt-3 flex cursor-pointer items-center gap-3 border border-dashed border-[#2f3b49] bg-[#0a0d12] p-3 transition-colors duration-150 hover:border-[#34d5c8]/70">
        <span class="grid h-16 w-16 shrink-0 place-items-center overflow-hidden border border-[#34d5c8]/30 bg-[#34d5c8]/10 text-[#34d5c8]">
          <img
            v-if="selectedImagePreviewUrl"
            class="h-full w-full object-cover"
            :src="selectedImagePreviewUrl"
            alt=""
          />
          <ImageUp v-else class="h-5 w-5" aria-hidden="true" />
        </span>
        <span class="min-w-0">
          <span class="block text-sm font-semibold text-[#f8fafc]">
            {{ isSearchingFace ? "正在匹配人物库" : selectedImageName || "选择图片" }}
          </span>
          <span class="block truncate text-xs text-[#7d8998]">
            InsightFace embedding / 相似度阈值过滤
          </span>
        </span>
        <input class="sr-only" type="file" accept="image/*" @change="handleImageInput" />
      </label>
      <div class="mt-3 border border-white/10 bg-[#0a0d12] p-3">
        <div class="flex items-center justify-between gap-3">
          <span class="text-xs font-semibold text-[#cbd5e1]">相似度阈值</span>
          <input
            class="h-8 w-20 border border-white/10 bg-[#090d12] px-2 text-right text-xs text-[#eef2f7] focus-visible:border-[#34d5c8] focus-visible:outline-none"
            type="number"
            min="0"
            max="1"
            step="0.01"
            :value="faceMinSimilarity.toFixed(2)"
            @input="updateFaceMinSimilarity(($event.target as HTMLInputElement).value)"
          />
        </div>
        <input
          class="mt-3 w-full accent-[#34d5c8]"
          type="range"
          min="0"
          max="1"
          step="0.01"
          :value="faceMinSimilarity"
          @input="updateFaceMinSimilarity(($event.target as HTMLInputElement).value)"
        />
        <div class="mt-2 flex justify-between text-[11px] text-[#697586]">
          <span>宽松</span>
          <span>严格</span>
        </div>
      </div>
    </div>

    <p v-if="errorMessage" class="mt-4 border border-[#ff5a5a]/30 bg-[#2a1111] px-3 py-2 text-xs text-[#ffb4b4]">
      {{ errorMessage }}
    </p>
  </aside>
</template>

<script setup lang="ts">
import { ImageUp, Search } from "@lucide/vue";

/** 搜索筛选栏接收的输入状态。 */
defineProps<{
  query: string;
  faceMinSimilarity: number;
  selectedImageName: string;
  selectedImagePreviewUrl: string;
  isSearchingText: boolean;
  isSearchingFace: boolean;
  errorMessage: string;
}>();

/** 搜索筛选栏向搜索页提交文本或图片搜索。 */
const emit = defineEmits<{
  "update:query": [value: string];
  "update:faceMinSimilarity": [value: number];
  textSearch: [];
  imageSearch: [file: File];
}>();

/** 读取文件选择器中的图片并触发以图搜图。 */
function handleImageInput(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  emit("imageSearch", file);
  input.value = "";
}

/** 更新以图搜图相似度阈值，限制在 0~1。 */
function updateFaceMinSimilarity(value: string) {
  const nextValue = Number(value);
  if (!Number.isFinite(nextValue)) return;
  emit("update:faceMinSimilarity", Math.min(Math.max(nextValue, 0), 1));
}
</script>

<template>
  <section class="min-h-0 overflow-y-auto bg-[#080a0d]">
    <div class="border-b border-white/10 bg-[#0f1319] px-5 py-4">
      <div class="flex items-center justify-between gap-4">
        <div>
          <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#697586]">Results</p>
          <h2 class="mt-1 text-sm font-semibold text-[#f8fafc]">
            {{ textResults.length }} 个文本结果 / {{ faceResults.length }} 个图片结果
          </h2>
        </div>
        <button
          class="h-9 border border-white/10 bg-[#151b23] px-3 text-xs font-semibold text-[#cbd5e1] transition-colors duration-150 hover:border-[#34d5c8]/60 hover:text-[#34d5c8]"
          type="button"
          @click="$emit('clear')"
        >
          清空
        </button>
      </div>
    </div>

    <div class="grid gap-0 lg:grid-cols-[minmax(0,1fr)_360px]">
      <div class="min-w-0">
        <div v-if="textResults.length === 0" class="px-5 py-16 text-sm text-[#7d8998]">
          暂无文本搜索结果。
        </div>
        <article
          v-for="item in textResults"
          :key="`${item.video_id}-${item.person_id}`"
          class="border-b border-white/10 px-5 py-4 transition-colors duration-150 hover:bg-[#111820]"
        >
          <div class="flex gap-4">
            <img
              v-if="item.representative_face_path"
              class="h-16 w-16 shrink-0 object-cover"
              :src="mediaUrl(item.representative_face_path)"
              alt=""
            />
            <span v-else class="grid h-16 w-16 shrink-0 place-items-center border border-white/10 bg-[#0a0d12] text-[#536171]">
              <User class="h-6 w-6" aria-hidden="true" />
            </span>
            <span class="min-w-0 flex-1">
              <span class="flex flex-wrap items-center gap-2">
                <span class="text-sm font-semibold text-[#f8fafc]">{{ item.label }}</span>
                <span v-if="item.global_person_id" class="timecode text-xs text-[#34d5c8]">
                  {{ item.global_person_id }}
                </span>
              </span>
              <span class="mt-1 block truncate text-xs text-[#7d8998]">{{ item.video_title }}</span>
              <span class="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-[#8f9bac]">
                <span>{{ item.appearances }} 片段</span>
                <span>{{ formatDuration(item.total_duration) }}</span>
                <span>{{ item.detection_count }} detections</span>
              </span>
            </span>
          </div>
        </article>
      </div>

      <aside class="min-h-0 border-l border-white/10 bg-[#0f1319]">
        <div class="border-b border-white/10 px-4 py-3">
          <p class="text-sm font-semibold text-[#f8fafc]">图片匹配</p>
        </div>
        <div v-if="isSearchingFace" class="px-4 py-10 text-sm text-[#7d8998]">
          正在用上传图片的人脸 embedding 匹配人物库。
        </div>
        <div v-else-if="selectedImageName && faceResults.length === 0" class="px-4 py-10 text-sm text-[#7d8998]">
          没有找到达到相似度阈值的人物。可以换更清晰的正脸图，或调整人物库匹配阈值。
        </div>
        <div v-else-if="faceResults.length === 0" class="px-4 py-10 text-sm text-[#7d8998]">
          暂无图片搜索结果。
        </div>
        <div
          v-for="item in faceResults"
          :key="item.global_person_id"
          class="border-b border-white/10 px-4 py-4"
        >
          <div class="flex gap-3">
            <img
              v-if="item.representative_face_path"
              class="h-14 w-14 shrink-0 object-cover"
              :src="mediaUrl(item.representative_face_path)"
              alt=""
            />
            <span v-else class="grid h-14 w-14 shrink-0 place-items-center border border-white/10 bg-[#0a0d12] text-[#536171]">
              <User class="h-5 w-5" aria-hidden="true" />
            </span>
            <div class="min-w-0">
              <p class="truncate text-sm font-semibold text-[#f8fafc]">
                {{ item.label ?? item.global_person_id }}
              </p>
              <p class="timecode mt-1 text-xs text-[#34d5c8]">
                相似度 {{ Math.round(item.similarity * 100) }}%
              </p>
              <p class="mt-1 text-xs text-[#7d8998]">
                {{ item.observation_count }} 次观测 / 阈值 {{ Math.round(item.threshold * 100) }}%
              </p>
            </div>
          </div>
        </div>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
import { User } from "@lucide/vue";

import { mediaUrl, type FaceSearchResult, type PeopleSearchResult } from "../../api";

/** 搜索结果列表接收的文本和人脸匹配结果。 */
defineProps<{
  textResults: PeopleSearchResult[];
  faceResults: FaceSearchResult[];
  selectedImageName: string;
  isSearchingFace: boolean;
}>();

/** 搜索结果列表向父级发出清空请求。 */
defineEmits<{
  clear: [];
}>();

/** 将秒数格式化成结果卡片中的时间长度。 */
function formatDuration(seconds: number) {
  const totalSeconds = Math.max(Math.round(seconds), 0);
  const minutes = Math.floor(totalSeconds / 60);
  const restSeconds = totalSeconds % 60;
  return `${minutes}:${String(restSeconds).padStart(2, "0")}`;
}
</script>

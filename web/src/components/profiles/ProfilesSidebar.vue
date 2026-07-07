<template>
  <aside class="grid h-full min-h-0 max-h-full grid-rows-[auto_minmax(0,1fr)] overflow-hidden border-r border-white/10 bg-[#0d1117]">
    <div class="border-b border-white/10 px-4 py-3">
      <div class="flex items-center justify-between gap-3">
        <div class="min-w-0">
          <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#697586]">Profiles</p>
          <h1 class="mt-1 truncate text-sm font-semibold text-[#f8fafc]">人物档案</h1>
        </div>
        <button
          class="grid h-9 w-9 shrink-0 place-items-center border border-white/10 bg-[#151b23] text-[#cbd5e1] transition-colors duration-150 hover:border-[#34d5c8]/60 hover:text-[#34d5c8] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]"
          type="button"
          aria-label="刷新人物档案"
          @click="emit('refresh')"
        >
          <RefreshCw class="h-4 w-4" aria-hidden="true" />
        </button>
      </div>

      <div class="mt-3 grid grid-cols-3 border border-white/10 bg-[#090d12] p-1">
        <button
          v-for="mode in browseModes"
          :key="mode.value"
          class="h-8 text-xs font-semibold text-[#8f9bac] transition-colors duration-150 hover:text-[#f8fafc]"
          :class="browseMode === mode.value ? 'bg-[#22313a] text-[#34d5c8]' : ''"
          type="button"
          @click="emit('update:browseMode', mode.value)"
        >
          {{ mode.label }}
        </button>
      </div>

      <label class="mt-3 flex h-9 items-center gap-2 border border-white/10 bg-[#090d12] px-3">
        <Search class="h-4 w-4 text-[#697586]" aria-hidden="true" />
        <input
          :value="query"
          class="min-w-0 flex-1 bg-transparent text-sm text-[#eef2f7] outline-none placeholder:text-[#536171]"
          type="search"
          :placeholder="searchPlaceholder"
          @input="emit('update:query', ($event.target as HTMLInputElement).value)"
        />
      </label>
      <div class="mt-3 inline-flex h-8 w-full items-center justify-center gap-2 border border-white/10 bg-[#151b23] px-3 text-xs font-semibold text-[#8f9bac]">
        <EyeOff class="h-4 w-4" aria-hidden="true" />
        隐藏项靠后显示
      </div>
      <form class="mt-3 border border-white/10 bg-[#090d12] p-3" @submit.prevent="emit('submitManualProfile')">
        <label class="block">
          <span class="mb-1 block text-xs text-[#7d8998]">
            {{ selectedLocalPersonTarget ? "用已选素材新建档案" : "手动新建空档案" }}
          </span>
          <input
            :value="manualProfileLabel"
            autocomplete="off"
            class="h-9 w-full border border-white/10 bg-[#0f151c] px-3 text-sm text-[#eef2f7] placeholder:text-[#536171] focus-visible:border-[#34d5c8] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]/60"
            name="manualProfileLabel"
            :placeholder="selectedLocalPersonTarget ? selectedLocalPersonTarget.label : '人物名称'"
            @input="emit('update:manualProfileLabel', ($event.target as HTMLInputElement).value)"
          />
        </label>
        <p v-if="selectedLocalPersonTarget" class="mt-2 text-[11px] leading-5 text-[#8f9bac]">
          已选 {{ formatCount(selectedLocalPersonTarget.referenceCount) }} 张：{{ selectedLocalPersonTarget.workTitle }} / {{ selectedLocalPersonTarget.label }}
        </p>
        <p v-else-if="selectedReferenceCount > 0" class="mt-2 text-[11px] leading-5 text-[#ffb4b4]">
          新建档案需要只选择同一作品里的同一个人物。
        </p>
        <button
          class="mt-2 inline-flex h-9 w-full items-center justify-center gap-2 bg-[#34d5c8] px-3 text-sm font-semibold text-[#061211] transition-colors duration-150 hover:bg-[#74f2e8] disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]"
          type="submit"
          :disabled="!canSubmitManualProfile"
        >
          <UserRound class="h-4 w-4" aria-hidden="true" />
          {{ selectedLocalPersonTarget ? "新建并关联已选人物" : "新建人物档案" }}
        </button>
      </form>
    </div>

    <div class="profile-list min-h-0 overflow-y-scroll overscroll-contain">
      <template v-if="browseMode === 'person'">
        <button
          v-for="person in filteredProfiles"
          :key="person.global_person_id"
          class="flex w-full items-center gap-3 border-b border-white/10 px-4 py-3 text-left transition-colors duration-150 hover:bg-[#121923] focus-visible:outline focus-visible:outline-2 focus-visible:outline-inset focus-visible:outline-[#34d5c8]"
          :class="selectedProfileId === person.global_person_id ? 'bg-[#16242a]' : ''"
          type="button"
          @click="emit('selectProfile', person.global_person_id)"
        >
          <img
            v-if="person.representative_face_path"
            class="h-12 w-12 shrink-0 object-cover"
            :src="mediaUrl(person.representative_face_path)"
            alt=""
          />
          <span v-else class="grid h-12 w-12 shrink-0 place-items-center border border-white/10 bg-[#090d12] text-[#536171]">
            <UserRound class="h-5 w-5" aria-hidden="true" />
          </span>
          <span class="min-w-0 flex-1">
            <span class="block truncate text-sm font-semibold text-[#f8fafc]">{{ profileName(person) }}</span>
            <span class="timecode mt-1 block truncate text-[11px] text-[#34d5c8]">{{ person.global_person_id }}</span>
            <span class="mt-1 flex gap-3 text-xs text-[#8f9bac]">
              <span>{{ formatCount(person.observation_count) }} 观测</span>
              <span>{{ formatDuration(person.total_duration) }}</span>
              <span>{{ formatCount(person.four_view_asset_count) }} 四视图</span>
            </span>
          </span>
        </button>
        <div v-if="!isLoading && filteredProfiles.length === 0" class="px-4 py-10 text-sm text-[#7d8998]">
          暂无人物档案。
        </div>
      </template>

      <template v-else-if="browseMode === 'work'">
        <button
          v-for="video in filteredVideos"
          :key="video.id"
          class="flex w-full items-center gap-3 border-b border-white/10 px-4 py-3 text-left transition-colors duration-150 hover:bg-[#121923] focus-visible:outline focus-visible:outline-2 focus-visible:outline-inset focus-visible:outline-[#34d5c8]"
          :class="selectedVideoId === video.id ? 'bg-[#16242a]' : ''"
          type="button"
          @click="emit('selectWork', video.id)"
        >
          <span class="grid h-12 w-12 shrink-0 place-items-center border border-white/10 bg-[#090d12] text-[#536171]">
            <Film class="h-5 w-5" aria-hidden="true" />
          </span>
          <span class="min-w-0 flex-1">
            <span class="block truncate text-sm font-semibold text-[#f8fafc]">{{ videoDisplayTitle(video) }}</span>
            <span class="mt-1 block truncate text-[11px] text-[#7d8998]">
              {{ video.source_directory || video.series_name || "未记录来源目录" }}
            </span>
            <span class="mt-1 flex gap-3 text-xs text-[#8f9bac]">
              <span>{{ formatCount(video.people_count) }} 人</span>
              <span>{{ formatDuration(video.duration_seconds) }}</span>
            </span>
          </span>
        </button>
        <div v-if="!isLoading && filteredVideos.length === 0" class="px-4 py-10 text-sm text-[#7d8998]">
          暂无作品。
        </div>
      </template>

      <template v-if="browseMode === 'trash'">
        <div
          v-for="person in filteredDeletedProfiles"
          :key="person.global_person_id"
          class="border-b border-white/10 px-4 py-3"
        >
          <div class="flex items-center gap-3">
            <img
              v-if="person.representative_face_path"
              class="h-12 w-12 shrink-0 object-cover opacity-70"
              :src="mediaUrl(person.representative_face_path)"
              alt=""
            />
            <span v-else class="grid h-12 w-12 shrink-0 place-items-center border border-white/10 bg-[#090d12] text-[#536171]">
              <UserRound class="h-5 w-5" aria-hidden="true" />
            </span>
            <span class="min-w-0 flex-1">
              <span class="block truncate text-sm font-semibold text-[#f8fafc]">{{ profileName(person) }}</span>
              <span class="timecode mt-1 block truncate text-[11px] text-[#f87171]">{{ person.global_person_id }}</span>
              <span class="mt-1 block truncate text-xs text-[#8f9bac]">
                删除于 {{ formatDateTime(person.deleted_at) }}
              </span>
            </span>
          </div>
          <div class="mt-3 grid grid-cols-2 gap-2">
            <button
              class="h-8 border border-[#34d5c8]/45 bg-[#102322] px-2 text-xs font-semibold text-[#9ff4ec] transition-colors duration-150 hover:bg-[#15302e] disabled:opacity-45"
              type="button"
              :disabled="isRestoringProfile"
              @click="emit('restoreProfile', person)"
            >
              恢复
            </button>
            <button
              class="h-8 border border-[#7f2e2e] bg-[#2a1215] px-2 text-xs font-semibold text-[#fecaca] transition-colors duration-150 hover:bg-[#35171b] disabled:opacity-45"
              type="button"
              :disabled="isPurgingProfile"
              @click="emit('purgeProfile', person)"
            >
              彻底删除
            </button>
          </div>
        </div>
        <div v-if="!isLoading && filteredDeletedProfiles.length === 0" class="px-4 py-10 text-sm text-[#7d8998]">
          回收站为空。
        </div>
      </template>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { EyeOff, Film, RefreshCw, Search, UserRound } from "@lucide/vue";

import { mediaUrl, type GlobalPersonItem, type VideoItem } from "../../api";

/** 人物档案侧栏的三种浏览入口。 */
type BrowseMode = "person" | "work" | "trash";

/** 用同一作品同一人物的参考素材新建档案时，父页面传入的可关联目标。 */
type SelectedLocalPersonTarget = {
  videoId: number;
  personId: number;
  label: string;
  workTitle: string;
  previousGlobalPersonId: string | null;
  referenceCount: number;
};

/** 侧栏只消费父页面过滤后的列表和选择状态，不在组件内发起数据请求。 */
defineProps<{
  browseMode: BrowseMode;
  query: string;
  manualProfileLabel: string;
  searchPlaceholder: string;
  filteredProfiles: GlobalPersonItem[];
  filteredVideos: VideoItem[];
  filteredDeletedProfiles: GlobalPersonItem[];
  selectedProfileId: string | null;
  selectedVideoId: number | null;
  selectedLocalPersonTarget: SelectedLocalPersonTarget | null;
  selectedReferenceCount: number;
  canSubmitManualProfile: boolean;
  isLoading: boolean;
  isRestoringProfile: boolean;
  isPurgingProfile: boolean;
}>();

/** 侧栏中的切换、搜索、选择和回收站操作全部上抛给档案页集中处理。 */
const emit = defineEmits<{
  "update:browseMode": [mode: BrowseMode];
  "update:query": [value: string];
  "update:manualProfileLabel": [value: string];
  refresh: [];
  submitManualProfile: [];
  selectProfile: [globalPersonId: string];
  selectWork: [videoId: number];
  restoreProfile: [person: GlobalPersonItem];
  purgeProfile: [person: GlobalPersonItem];
}>();

const numberFormatter = new Intl.NumberFormat("zh-CN");

/** 按固定顺序渲染顶部浏览模式分段按钮。 */
const browseModes: Array<{ value: BrowseMode; label: string }> = [
  { value: "person", label: "按人物" },
  { value: "work", label: "按作品" },
  { value: "trash", label: "回收站" },
];

/** 优先展示人工命名，未命名时回退到全局人物 ID。 */
function profileName(person: GlobalPersonItem) {
  return person.label?.trim() || person.global_person_id;
}

/** 作品列表标题优先使用元数据标题，其次使用原始文件名或路径。 */
function videoDisplayTitle(video: VideoItem) {
  return meaningfulTitle(video.title, video.original_filename || video.path || `Video ${video.id}`);
}

/** 统一处理空白标题，避免列表中出现空字符串。 */
function meaningfulTitle(primary: string | null | undefined, fallback: string) {
  const trimmed = primary?.trim();
  return trimmed && trimmed.length > 0 ? trimmed : fallback;
}

/** 格式化侧栏中的统计数量。 */
function formatCount(value: number) {
  return numberFormatter.format(value);
}

/** 将秒数压成适合侧栏展示的 mm:ss 或 h:mm:ss。 */
function formatDuration(seconds: number) {
  const safe = Math.max(Math.round(seconds), 0);
  const hours = Math.floor(safe / 3600);
  const minutes = Math.floor((safe % 3600) / 60);
  const restSeconds = safe % 60;
  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${String(restSeconds).padStart(2, "0")}`;
  }
  return `${minutes}:${String(restSeconds).padStart(2, "0")}`;
}

/** 回收站列表中的删除时间只展示月日和分钟。 */
function formatDateTime(value: string | null | undefined) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
</script>

<template>
  <section
    :ref="setReviewPanelRef"
    class="batch-panel grid min-h-0 grid-rows-[48px_minmax(0,1fr)] overflow-hidden border-t border-white/10 bg-[#0f1319]"
  >
    <div class="flex h-12 items-center justify-between border-b border-white/10 px-4">
      <div class="flex items-center gap-3">
        <Images class="h-4 w-4 text-[#34d5c8]" aria-hidden="true" />
        <h2 class="text-sm font-semibold">批量整理人脸</h2>
        <span class="text-xs text-[#7d8998]">
          {{ formatCount(trackReviewItems.length) }} 张代表脸
        </span>
      </div>
      <div class="flex items-center gap-2">
        <div class="flex items-center gap-1 border border-white/10 bg-[#0a0d12] px-1 py-1">
          <button
            v-for="option in reviewCardSizeOptions"
            :key="option.id"
            class="h-6 px-2 text-[11px] font-semibold transition-colors duration-150 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]"
            :class="reviewCardSize === option.id ? 'bg-[#34d5c8] text-[#061211]' : 'text-[#8f9bac] hover:text-[#34d5c8]'"
            type="button"
            @click="$emit('setReviewCardSize', option.id)"
          >
            {{ option.label }}
          </button>
        </div>
        <button
          class="h-8 border border-white/10 bg-[#151b23] px-3 text-xs font-semibold text-[#cbd5e1] transition-colors duration-150 hover:border-[#f5c451]/60 hover:text-[#f5c451] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#f5c451]"
          type="button"
          @click="$emit('focusReviewPanel')"
        >
          聚焦
        </button>
        <button
          class="h-8 border border-white/10 bg-[#151b23] px-3 text-xs font-semibold text-[#cbd5e1] transition-colors duration-150 hover:border-[#34d5c8]/60 hover:text-[#34d5c8] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]"
          type="button"
          :disabled="trackReviewItems.length === 0"
          @click="$emit('selectAllReviewTracks')"
        >
          全选
        </button>
        <button
          class="h-8 border border-white/10 bg-[#151b23] px-3 text-xs font-semibold text-[#cbd5e1] transition-colors duration-150 hover:border-[#34d5c8]/60 hover:text-[#34d5c8] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]"
          type="button"
          :disabled="selectedReviewTrackIds.length === 0"
          @click="$emit('clearReviewSelection')"
        >
          清空
        </button>
      </div>
    </div>

    <div class="grid min-h-0 grid-cols-[minmax(0,1fr)_260px] overflow-hidden">
      <div
        :ref="setReviewViewportRef"
        class="review-viewport relative min-h-0 overflow-y-auto p-4"
        @pointerdown="$emit('startReviewBoxSelect', $event)"
        @pointermove="$emit('moveReviewBoxSelect', $event)"
        @pointerup="$emit('finishReviewBoxSelect', $event)"
        @pointercancel="$emit('finishReviewBoxSelect', $event)"
      >
        <template v-if="trackReviewItems.length > 0">
          <div
            :ref="setReviewGridRef"
            class="review-grid grid grid-cols-[repeat(auto-fill,minmax(var(--review-card-min),1fr))] gap-3"
            :style="reviewGridStyle"
          >
            <button
              v-for="item in trackReviewItems"
              :key="item.track.id"
              class="review-card group min-w-0 border border-white/10 bg-[#0a0d12] p-2 text-left transition-colors duration-150 hover:border-[#34d5c8]/60 hover:bg-[#111b20] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]"
              :class="[
                selectedReviewTrackIds.includes(item.track.track_id) ? 'border-[#f5c451] bg-[#211b0f]' : '',
                reviewDragTrackIds.includes(item.track.track_id) ? 'opacity-45' : '',
                selectedPersonId !== null && item.track.person_id === selectedPersonId ? 'shadow-[inset_0_0_0_1px_rgba(52,213,200,0.45)]' : ''
              ]"
              type="button"
              :aria-pressed="selectedReviewTrackIds.includes(item.track.track_id)"
              :data-track-id="item.track.track_id"
              :ref="(el) => setReviewCardRef(el, item.track.track_id)"
              @click.stop="$emit('toggleReviewTrack', item.track.track_id, item.track)"
            >
              <span class="relative block aspect-square overflow-hidden bg-[#151b23]">
                <img
                  v-if="item.facePath"
                  class="h-full w-full object-cover transition-transform duration-150 group-hover:scale-[1.04]"
                  :src="mediaUrl(item.facePath)"
                  :alt="`${item.personLabel} Track ${item.track.track_id}`"
                  draggable="false"
                  loading="lazy"
                />
                <span v-else class="grid h-full w-full place-items-center text-[#697586]">
                  <Image class="h-7 w-7" aria-hidden="true" />
                </span>
                <span
                  class="absolute left-2 top-2 grid h-5 w-5 place-items-center border text-[11px] font-bold"
                  :class="selectedReviewTrackIds.includes(item.track.track_id)
                    ? 'border-[#f5c451] bg-[#f5c451] text-[#11151b]'
                    : 'border-white/30 bg-black/50 text-[#cbd5e1]'"
                >
                  {{ selectedReviewTrackIds.includes(item.track.track_id) ? "✓" : "" }}
                </span>
                <span
                  class="review-drag-handle absolute right-2 top-2 grid h-7 w-7 place-items-center border border-white/20 bg-black/55 text-[#cbd5e1] transition-colors duration-150 group-hover:border-[#34d5c8]/60 group-hover:text-[#34d5c8]"
                  title="拖动归类"
                  data-review-drag-handle="true"
                  @click.stop
                >
                  <GripVertical class="pointer-events-none h-4 w-4" aria-hidden="true" />
                </span>
              </span>
              <span class="mt-2 flex min-w-0 items-center justify-between gap-2">
                <span class="truncate text-xs font-semibold text-[#f8fafc]">
                  {{ item.personLabel }}
                </span>
                <span class="timecode shrink-0 text-[11px] text-[#34d5c8]">
                  {{ formatTime(item.track.start) }}
                </span>
              </span>
              <span class="mt-1 block truncate text-[11px] text-[#7d8998]">
                Track {{ item.track.track_id }} / {{ formatCount(item.track.detection_count) }} 检测
              </span>
            </button>
          </div>

          <div
            v-if="reviewSelectionRect"
            class="selection-rect pointer-events-none absolute z-20 border border-[#f5c451] bg-[#f5c451]/10"
            :style="reviewSelectionRectStyle"
            aria-hidden="true"
          />
        </template>

        <div v-else class="grid h-full place-items-center text-sm text-[#7d8998]">
          当前视频没有可整理的轨迹代表脸。
        </div>
      </div>

      <div class="min-h-0 overflow-y-auto border-l border-white/10 bg-[#0c1016] p-4">
        <div class="text-xs text-[#7d8998]">已选择</div>
        <div class="mt-1 text-2xl font-semibold text-[#f8fafc]">
          {{ formatCount(selectedReviewTrackIds.length) }}
        </div>
        <label class="mt-4 block">
          <span class="mb-1 block text-xs text-[#7d8998]">归类到人物</span>
          <select
            :value="bulkTargetPersonId ?? ''"
            class="h-10 w-full border border-white/10 bg-[#0a0d12] px-3 text-sm text-[#eef2f7] focus-visible:border-[#34d5c8] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]/60"
            :disabled="visiblePeople.length === 0"
            @change="$emit('update:bulkTargetPersonId', selectNumberOrNull($event))"
          >
            <option value="">选择目标人物</option>
            <option
              v-for="person in visiblePeople"
              :key="person.person_id"
              :value="person.person_id"
            >
              {{ person.label }}
            </option>
          </select>
        </label>
        <button
          class="mt-3 inline-flex h-10 w-full items-center justify-center gap-2 bg-[#34d5c8] px-3 text-sm font-semibold text-[#061211] transition-colors duration-150 hover:bg-[#74f2e8] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]"
          type="button"
          :disabled="selectedReviewTrackIds.length === 0 || bulkTargetPersonId === null || isReviewing"
          @click="$emit('submitBulkAssign')"
        >
          <Check class="h-4 w-4" aria-hidden="true" />
          统一归类
        </button>
        <button
          class="mt-2 inline-flex h-10 w-full items-center justify-center gap-2 border border-[#7f2e2e] bg-[#2a1215] px-3 text-sm font-semibold text-[#fecaca] transition-colors duration-150 hover:bg-[#35171b] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#f87171]"
          type="button"
          :disabled="selectedReviewTrackIds.length === 0 || isReviewing"
          @click="$emit('deleteSelectedTrackPeople')"
        >
          <Trash2 class="h-4 w-4" aria-hidden="true" />
          删除所选人物
        </button>
        <div class="mt-4 border border-white/10 bg-[#0a0d12] p-3 text-xs leading-5 text-[#8f9bac]">
          点选或框选代表脸后，按住右上角抓手拖到右侧/时间轴人物上归类。这里是轻量整理，不做逐帧标注。
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { Check, GripVertical, Image, Images, Trash2 } from "@lucide/vue";
import type { StyleValue } from "vue";

import { mediaUrl, type PersonItem, type TrackItem } from "../../api";

/** 审阅卡片尺寸档位，决定网格最小列宽。 */
type ReviewCardSize = "small" | "medium" | "large";

/** 顶部尺寸切换按钮和 CSS 网格宽度共用的配置。 */
type ReviewCardSizeOption = {
  id: ReviewCardSize;
  label: string;
  minWidth: number;
};

/** 一张轨迹代表脸卡片所需的展示数据。 */
type ReviewTrackItem = {
  track: TrackItem;
  personLabel: string;
  facePath: string | null;
};

/** 框选矩形使用滚动容器内坐标，避免页面滚动影响命中计算。 */
type ReviewSelectionRect = {
  startX: number;
  startY: number;
  currentX: number;
  currentY: number;
};

/** 批量整理面板的状态和 DOM ref setter 均由父页面传入，方便统一处理拖拽/框选。 */
defineProps<{
  trackReviewItems: ReviewTrackItem[];
  reviewCardSizeOptions: ReviewCardSizeOption[];
  reviewCardSize: ReviewCardSize;
  reviewGridStyle: StyleValue;
  selectedReviewTrackIds: number[];
  reviewDragTrackIds: number[];
  selectedPersonId: number | null;
  reviewSelectionRect: ReviewSelectionRect | null;
  reviewSelectionRectStyle: StyleValue;
  bulkTargetPersonId: number | null;
  visiblePeople: PersonItem[];
  isReviewing: boolean;
  setReviewPanelRef: (el: unknown) => void;
  setReviewViewportRef: (el: unknown) => void;
  setReviewGridRef: (el: unknown) => void;
  setReviewCardRef: (el: unknown, trackId: number) => void;
  formatCount: (value: number) => string;
  formatTime: (seconds: number) => string;
}>();

/** 面板只负责把用户交互上抛，真正的轨迹归类、删除和尺寸持久化在父页面完成。 */
defineEmits<{
  "update:bulkTargetPersonId": [value: number | null];
  setReviewCardSize: [value: ReviewCardSize];
  focusReviewPanel: [];
  selectAllReviewTracks: [];
  clearReviewSelection: [];
  startReviewBoxSelect: [event: PointerEvent];
  moveReviewBoxSelect: [event: PointerEvent];
  finishReviewBoxSelect: [event: PointerEvent];
  toggleReviewTrack: [trackId: number, track: TrackItem];
  submitBulkAssign: [];
  deleteSelectedTrackPeople: [];
}>();

/** 将 select 的空字符串转换成 null，合法数值转换成人物 ID。 */
function selectNumberOrNull(event: Event) {
  if (!(event.target instanceof HTMLSelectElement) || event.target.value === "") return null;
  const value = Number(event.target.value);
  return Number.isFinite(value) ? value : null;
}
</script>

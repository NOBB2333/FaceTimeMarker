<template>
  <section
    class="timeline-panel min-h-0 bg-[#0b0f14]"
    tabindex="0"
    @keydown.capture="handleTimelineKeydown"
  >
    <div class="flex h-11 items-center justify-between gap-4 border-b border-white/10 px-4">
      <div class="flex items-center gap-3">
        <Activity class="h-4 w-4 text-[#34d5c8]" aria-hidden="true" />
        <h2 class="text-sm font-semibold">人物出现时间轴</h2>
      </div>
      <div class="flex min-w-0 items-center gap-3">
        <button
          class="h-7 border border-white/10 bg-[#151b23] px-2.5 text-xs font-semibold text-[#cbd5e1] transition-colors duration-150 hover:border-[#34d5c8]/60 hover:text-[#34d5c8] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]"
          type="button"
          title="显示完整时间轴"
          @click="resetTimelineZoom"
        >
          全部
        </button>
        <label class="hidden items-center gap-2 text-xs text-[#8f9bac] sm:flex" title="Ctrl + 滚轮围绕播放头缩放，Alt + 拖动或滚轮平移">
          <span>缩放</span>
          <input
            class="timeline-zoom-slider w-28"
            type="range"
            :min="minTimelineZoom"
            :max="maxTimelineZoom"
            step="0.25"
            :value="timelineZoom"
            aria-label="缩放人物出现时间轴"
            @input="updateTimelineZoomFromInput"
          />
          <span class="timecode w-9 text-right text-[#cbd5e1]">{{ timelineZoomLabel }}</span>
        </label>
        <div class="timecode text-xs text-[#8f9bac]">{{ formatTime(currentTime) }}</div>
      </div>
    </div>

    <div class="grid h-[calc(100%-44px)] grid-cols-[150px_minmax(0,1fr)] overflow-hidden">
      <div class="flex min-h-0 flex-col border-r border-white/10 bg-[#0f1319]">
        <div class="h-8 border-b border-white/10 px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-[#697586]">
          Tracks
        </div>
        <div
          ref="timelinePeopleListEl"
          class="timeline-people-scroll min-h-0 flex-1 overflow-y-auto"
          @scroll="syncTimelineScroll('people')"
        >
          <div
            v-for="person in people"
            :key="person.person_id"
              class="h-14 w-full border-b border-white/10 px-2 text-left transition-colors duration-150 hover:bg-[#151c24]"
            :class="[
              selectedPersonId === person.person_id ? 'bg-[#16232a]' : '',
              reviewDropTargetPersonId === person.person_id ? 'bg-[#1a2c25] shadow-[inset_3px_0_0_#34d5c8]' : ''
            ]"
            :data-person-drop-id="person.person_id"
            @dragenter.prevent="handleSegmentDragOver(person.person_id)"
            @dragover.prevent="handleSegmentDragOver(person.person_id)"
            @drop.prevent="handleSegmentDrop(person.person_id)"
          >
            <button
              class="flex h-full w-full min-w-0 items-center gap-2 px-1 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-inset focus-visible:outline-[#34d5c8]"
              type="button"
              @click="$emit('selectPerson', person.person_id)"
            >
              <img
                v-if="person.representative_face_path"
                class="h-8 w-8 shrink-0 object-cover"
                :src="mediaUrl(person.representative_face_path)"
                :alt="`${person.label} 代表脸`"
                width="32"
                height="32"
                loading="lazy"
              />
              <span v-else class="grid h-8 w-8 shrink-0 place-items-center bg-[#151b23] text-[#697586]">
                <User class="h-4 w-4" aria-hidden="true" />
              </span>
              <span class="min-w-0">
                <span class="block truncate text-xs font-semibold text-[#eef2f7]">{{ person.label }}</span>
                <span class="timecode block text-[11px] text-[#7d8998]">
                  {{ formatTime(person.total_duration) }}
                </span>
              </span>
            </button>
          </div>
        </div>
      </div>

      <div
        ref="timelineChartEl"
        class="timeline-chart-scroll relative min-w-0 overflow-auto"
        :class="isPanningTimeline ? 'cursor-grabbing select-none' : ''"
        @scroll="syncTimelineScroll('chart')"
        @wheel="handleTimelineWheel"
        @pointerdown.capture="startTimelinePan"
      >
        <div ref="timelineCanvasEl" class="timeline-canvas relative" :style="timelineCanvasStyle">
          <div
            class="ruler sticky top-0 z-20 grid h-8 border-b border-white/10 bg-[#0f1319]"
            :style="{ gridTemplateColumns: `repeat(${rulerTicks.length}, minmax(0, 1fr))` }"
            @pointerdown.stop="startTimelineSeek"
          >
            <div
              v-for="tick in rulerTicks"
              :key="tick"
              class="border-l border-white/10 px-2 py-2 text-[11px] text-[#697586]"
            >
              {{ formatTime(tick) }}
            </div>
          </div>

          <div
            v-if="durationSeconds > 0"
            class="timeline-playhead absolute bottom-0 top-0 z-30 w-4 -translate-x-2 cursor-ew-resize touch-none"
            :class="isSeekingTimeline ? 'is-dragging' : ''"
            :style="playheadStyle"
            role="slider"
            tabindex="0"
            aria-label="拖动播放头"
            :aria-valuemin="0"
            :aria-valuemax="Math.round(durationSeconds)"
            :aria-valuenow="Math.round(currentTime)"
            @keydown="handlePlayheadKeydown"
            @pointerdown="startTimelineSeek"
          >
            <span class="timeline-playhead-cap" />
          </div>

          <div v-if="people.length > 0">
            <div
              v-for="person in people"
              :key="person.person_id"
              class="relative h-14 border-b border-white/10 bg-[#0b0f14]"
              :class="[
                selectedPersonId === person.person_id ? 'bg-[#101d24]' : '',
                reviewDropTargetPersonId === person.person_id ? 'bg-[#12251f]' : ''
              ]"
              :data-person-drop-id="person.person_id"
              @dragenter.prevent="handleSegmentDragOver(person.person_id)"
              @dragover.prevent="handleSegmentDragOver(person.person_id)"
              @drop.prevent="handleSegmentDrop(person.person_id)"
            >
              <div
                v-for="segment in segmentsForPerson(person.person_id)"
                :key="segment.id"
                class="timeline-segment absolute top-[13px] flex h-7 overflow-hidden bg-[#1fb6a8] text-[11px] font-semibold text-[#041211] shadow-[0_0_0_1px_rgba(255,255,255,0.16)] transition-[transform,background-color,box-shadow,opacity] duration-150 hover:bg-[#34d5c8]"
                :class="[
                  activeSegmentId === segment.id ? 'bg-[#f5c451] text-[#11151b]' : '',
                  selectedPersonId !== null && selectedPersonId !== person.person_id ? 'opacity-35' : '',
                  draggedSegment?.id === segment.id ? 'scale-[0.98] opacity-55' : ''
                ]"
                :style="segmentStyle(segment)"
                draggable="true"
                :aria-label="`跳转到 ${person.label} ${formatTime(segment.start)}`"
                @dragstart="startSegmentDrag(segment, $event)"
                @dragend="finishSegmentDrag"
              >
                <button
                  class="h-full w-full min-w-0 px-2 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#f5c451]"
                  type="button"
                  @click="$emit('jumpToSegment', segment)"
                >
                  <span class="timecode block truncate">{{ formatTime(segment.start) }}</span>
                </button>
              </div>
            </div>
          </div>

          <div v-else class="px-5 py-10 text-sm text-[#7d8998]">
            当前视频没有可展示的人物轨道。
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { Activity, User } from "@lucide/vue";
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

import { mediaUrl, type PersonItem, type SegmentItem } from "../../api";
import { clamp, formatTime } from "./workspaceUtils";

/** 时间轴组件接收的人物、片段和播放状态。 */
const props = defineProps<{
  people: PersonItem[];
  segments: SegmentItem[];
  selectedPersonId: number | null;
  activeSegmentId: number | null;
  reviewDropTargetPersonId: number | null;
  currentTime: number;
  durationSeconds: number;
}>();

/** 时间轴组件向工作台同步选择、定位和拖拽动作。 */
const emit = defineEmits<{
  selectPerson: [personId: number];
  jumpToSegment: [segment: SegmentItem];
  seekTime: [seconds: number];
  togglePlayback: [];
  segmentDragStart: [segment: SegmentItem];
  segmentDragTarget: [personId: number | null];
  segmentDrop: [segment: SegmentItem, targetPersonId: number];
  segmentDragEnd: [];
  deletePerson: [personId: number];
  deleteSegment: [segment: SegmentItem];
}>();

/** 左侧人物列表滚动容器。 */
const timelinePeopleListEl = ref<HTMLElement | null>(null);
/** 右侧时间轴滚动容器。 */
const timelineChartEl = ref<HTMLElement | null>(null);
/** 用于换算指针位置的时间轴画布。 */
const timelineCanvasEl = ref<HTMLElement | null>(null);
/** 标记当前是否正在拖动播放头。 */
const isSeekingTimeline = ref(false);
/** 标记当前是否正在拖动平移时间轴。 */
const isPanningTimeline = ref(false);
/** 当前拖拽中的片段。 */
const draggedSegment = ref<SegmentItem | null>(null);
/** 当前时间轴可视区宽度，1x 缩放时用它完整展示全片。 */
const timelineViewportWidth = ref(0);
let syncingTimelineScroll = false;
let timelineResizeObserver: ResizeObserver | null = null;
let panStartClientX = 0;
let panStartScrollLeft = 0;
const maxTimelineCanvasWidth = 48000;
const minTimelineZoom = 1;
const maxTimelineZoom = 16;
const timelineZoom = ref(1);

onMounted(() => {
  updateTimelineViewportWidth();
  timelineResizeObserver = new ResizeObserver(updateTimelineViewportWidth);
  if (timelineChartEl.value) {
    timelineResizeObserver.observe(timelineChartEl.value);
  }
});

onBeforeUnmount(() => {
  stopTimelineSeek();
  stopTimelinePan();
  finishSegmentDrag();
  timelineResizeObserver?.disconnect();
  timelineResizeObserver = null;
});

watch(
  () => props.durationSeconds,
  () => {
    resetTimelineZoom();
  },
);

/** 计算时间轴顶部标尺刻度。 */
const rulerTicks = computed(() => {
  const duration = Math.max(props.durationSeconds, 1);
  const tickCount = 8;
  return Array.from({ length: tickCount + 1 }, (_, index) => (duration / tickCount) * index);
});
/** 计算播放头在时间轴上的位置。 */
const playheadStyle = computed(() => {
  const duration = Math.max(props.durationSeconds, 1);
  const left = Math.min(Math.max((props.currentTime / duration) * 100, 0), 100);
  return {
    left: `${left}%`
  };
});
const timelineCanvasWidth = computed(() => {
  const viewport = Math.max(Math.round(timelineViewportWidth.value || 960), 1);
  return Math.min(Math.max(Math.round(viewport * timelineZoom.value), viewport), maxTimelineCanvasWidth);
});
const timelineCanvasStyle = computed(() => {
  return {
    width: `${timelineCanvasWidth.value}px`,
  };
});
const timelineZoomLabel = computed(() => `${timelineZoom.value.toFixed(timelineZoom.value % 1 === 0 ? 0 : 2)}x`);

/** 记录时间轴可见宽度，默认视图始终显示完整视频时长。 */
function updateTimelineViewportWidth() {
  const chart = timelineChartEl.value;
  timelineViewportWidth.value = chart?.clientWidth ?? 0;
  if (timelineZoom.value === minTimelineZoom && chart) {
    chart.scrollLeft = 0;
  }
}

/** 将时间轴缩放恢复为全览。 */
function resetTimelineZoom() {
  timelineZoom.value = minTimelineZoom;
  window.requestAnimationFrame(() => {
    if (timelineChartEl.value) {
      timelineChartEl.value.scrollLeft = 0;
    }
  });
}

/** 通过滑杆调整时间轴缩放，并尽量保持当前播放头位置不跳动。 */
function updateTimelineZoomFromInput(event: Event) {
  const input = event.target as HTMLInputElement | null;
  if (!input) return;
  setTimelineZoom(Number(input.value));
}

/** 设置时间轴缩放倍数，围绕当前播放头红线进行缩放。 */
function setTimelineZoom(nextZoom: number) {
  const chart = timelineChartEl.value;
  const oldWidth = timelineCanvasWidth.value;
  const duration = Math.max(props.durationSeconds, 1);
  const anchorRatio = Math.min(Math.max(props.currentTime / duration, 0), 1);
  const anchorCanvasX = oldWidth * anchorRatio;
  const viewportX = chart
    ? Math.min(Math.max(anchorCanvasX - chart.scrollLeft, 0), chart.clientWidth)
    : 0;
  timelineZoom.value = clamp(nextZoom, minTimelineZoom, maxTimelineZoom);
  window.requestAnimationFrame(() => {
    const nextChart = timelineChartEl.value;
    if (!nextChart) return;
    const nextWidth = timelineCanvasWidth.value;
    const maxScrollLeft = Math.max(nextWidth - nextChart.clientWidth, 0);
    nextChart.scrollLeft = Math.min(Math.max(anchorRatio * nextWidth - viewportX, 0), maxScrollLeft);
  });
}

/** Ctrl/Command 滚轮缩放，Alt 滚轮横向平移。 */
function handleTimelineWheel(event: WheelEvent) {
  const chart = timelineChartEl.value;
  if (!chart) return;
  if (event.ctrlKey || event.metaKey) {
    event.preventDefault();
    const direction = event.deltaY > 0 ? -1 : 1;
    const zoomFactor = direction > 0 ? 1.18 : 1 / 1.18;
    setTimelineZoom(timelineZoom.value * zoomFactor);
    return;
  }
  if (event.altKey) {
    event.preventDefault();
    const delta = Math.abs(event.deltaX) > Math.abs(event.deltaY) ? event.deltaX : event.deltaY;
    chart.scrollLeft += delta;
  }
}

/** Alt + 拖动时间轴时横向平移，不改变播放头。 */
function startTimelinePan(event: PointerEvent) {
  const chart = timelineChartEl.value;
  if (!chart || !event.altKey || event.button !== 0) return;
  event.preventDefault();
  event.stopPropagation();
  isPanningTimeline.value = true;
  panStartClientX = event.clientX;
  panStartScrollLeft = chart.scrollLeft;
  window.addEventListener("pointermove", moveTimelinePan);
  window.addEventListener("pointerup", stopTimelinePan);
  window.addEventListener("pointercancel", stopTimelinePan);
}

/** 拖动平移时同步横向滚动。 */
function moveTimelinePan(event: PointerEvent) {
  if (!isPanningTimeline.value || !timelineChartEl.value) return;
  event.preventDefault();
  timelineChartEl.value.scrollLeft = panStartScrollLeft - (event.clientX - panStartClientX);
}

/** 停止 Alt 平移并移除全局监听。 */
function stopTimelinePan() {
  if (!isPanningTimeline.value) return;
  isPanningTimeline.value = false;
  window.removeEventListener("pointermove", moveTimelinePan);
  window.removeEventListener("pointerup", stopTimelinePan);
  window.removeEventListener("pointercancel", stopTimelinePan);
}

/** 同步人物列表和时间轴区域的垂直滚动。 */
function syncTimelineScroll(source: "people" | "chart") {
  if (syncingTimelineScroll) return;
  const peopleList = timelinePeopleListEl.value;
  const chart = timelineChartEl.value;
  if (!peopleList || !chart) return;
  syncingTimelineScroll = true;
  if (source === "people") {
    chart.scrollTop = peopleList.scrollTop;
  } else {
    peopleList.scrollTop = chart.scrollTop;
  }
  window.requestAnimationFrame(() => {
    syncingTimelineScroll = false;
  });
}

/** 开始通过指针拖动播放头定位。 */
function startTimelineSeek(event: PointerEvent) {
  if (event.button !== 0) return;
  event.preventDefault();
  isSeekingTimeline.value = true;
  seekFromPointer(event);
  window.addEventListener("pointermove", moveTimelineSeek);
  window.addEventListener("pointerup", stopTimelineSeek);
  window.addEventListener("pointercancel", stopTimelineSeek);
}

/** 拖动播放头时持续同步时间。 */
function moveTimelineSeek(event: PointerEvent) {
  if (!isSeekingTimeline.value) return;
  event.preventDefault();
  seekFromPointer(event);
}

/** 停止拖动播放头并移除全局监听。 */
function stopTimelineSeek() {
  if (!isSeekingTimeline.value) return;
  isSeekingTimeline.value = false;
  window.removeEventListener("pointermove", moveTimelineSeek);
  window.removeEventListener("pointerup", stopTimelineSeek);
  window.removeEventListener("pointercancel", stopTimelineSeek);
}

/** 根据指针位置换算要跳转的视频时间。 */
function seekFromPointer(event: PointerEvent) {
  const canvas = timelineCanvasEl.value;
  if (!canvas || props.durationSeconds <= 0) return;
  const rect = canvas.getBoundingClientRect();
  const ratio = Math.min(Math.max((event.clientX - rect.left) / rect.width, 0), 1);
  emit("seekTime", ratio * props.durationSeconds);
}

/** 处理播放头的键盘微调快捷键。 */
function handlePlayheadKeydown(event: KeyboardEvent) {
  const smallStep = event.shiftKey ? 0.5 : 1;
  const largeStep = event.shiftKey ? 3 : 5;
  let nextTime: number | null = null;
  if (event.key === "ArrowLeft") nextTime = props.currentTime - smallStep;
  if (event.key === "ArrowRight") nextTime = props.currentTime + smallStep;
  if (event.key === "PageUp") nextTime = props.currentTime + largeStep;
  if (event.key === "PageDown") nextTime = props.currentTime - largeStep;
  if (event.key === "Home") nextTime = 0;
  if (event.key === "End") nextTime = props.durationSeconds;
  if (nextTime === null) return;
  event.preventDefault();
  emit("seekTime", Math.min(Math.max(nextTime, 0), props.durationSeconds));
}

/** 处理时间轴区域的播放和删除键盘操作。 */
function handleTimelineKeydown(event: KeyboardEvent) {
  if (event.target instanceof HTMLElement && isTypingTarget(event.target)) return;
  if (event.code === "Space" || event.key === " ") {
    event.preventDefault();
    emit("togglePlayback");
    return;
  }
  if (event.key !== "Delete") return;
  const activeSegment = props.segments.find((segment) => segment.id === props.activeSegmentId);
  if (activeSegment) {
    event.preventDefault();
    emit("deleteSegment", activeSegment);
    return;
  }
  if (props.selectedPersonId !== null) {
    event.preventDefault();
    emit("deletePerson", props.selectedPersonId);
  }
}

/** 判断键盘事件是否来自可输入控件。 */
function isTypingTarget(target: HTMLElement) {
  const tagName = target.tagName.toLowerCase();
  return tagName === "input" || tagName === "textarea" || tagName === "select" || target.isContentEditable;
}

/** 开始拖拽时间轴片段。 */
function startSegmentDrag(segment: SegmentItem, event: DragEvent) {
  draggedSegment.value = segment;
  event.dataTransfer?.setData(
    "application/x-facetimemarker-segment",
    JSON.stringify({ segmentId: segment.id, personId: segment.person_id }),
  );
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = "move";
  }
  emit("segmentDragStart", segment);
  emit("segmentDragTarget", null);
}

/** 更新片段拖拽时的人物投放目标。 */
function handleSegmentDragOver(personId: number) {
  const segment = draggedSegment.value;
  emit("segmentDragTarget", segment && segment.person_id !== personId ? personId : null);
}

/** 将拖拽片段投放到目标人物轨道。 */
function handleSegmentDrop(personId: number) {
  const segment = draggedSegment.value;
  if (segment && segment.person_id !== personId) {
    emit("segmentDrop", segment, personId);
  }
  finishSegmentDrag();
}

/** 清理片段拖拽状态。 */
function finishSegmentDrag() {
  if (!draggedSegment.value) return;
  draggedSegment.value = null;
  emit("segmentDragTarget", null);
  emit("segmentDragEnd");
}

/** 获取指定人物在时间轴上的片段。 */
function segmentsForPerson(personId: number) {
  return props.segments.filter((segment) => segment.person_id === personId);
}

/** 将片段起止时间转换为时间轴条样式。 */
function segmentStyle(segment: SegmentItem) {
  const duration = Math.max(props.durationSeconds, 1);
  const left = Math.max((segment.start / duration) * 100, 0);
  const width = Math.max(((segment.end - segment.start) / duration) * 100, 0.7);
  return {
    left: `${left}%`,
    width: `${Math.min(width, 100 - left)}%`
  };
}

</script>

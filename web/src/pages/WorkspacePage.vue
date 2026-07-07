<template>
  <main class="app-shell h-full overflow-hidden bg-[#090b0f] text-[#eef2f7]">
    <a class="skip-link" href="#workspace">跳到工作区</a>

      <WorkspaceHeader
        v-model:selected-preset="selectedPreset"
        :videos-count="videos.length"
        :people-count="visiblePeople.length"
        :segments-count="segments.length"
      :current-time="currentTime"
      :presets="presets"
      @refresh="refreshAll"
    />

    <section id="workspace" class="workspace-grid bg-[#090b0f]">
      <MediaSidebar
        v-model:server-video-path="serverVideoPath"
        v-model:timeline-path="timelinePath"
        v-model:video-query="videoQuery"
        v-model:series-name="analysisSeriesName"
        v-model:config-path="analysisConfigPath"
        :videos="videos"
        :trash-videos="trashVideos"
        :selected-video-id="selectedVideo?.id ?? null"
        :is-busy="isBusy"
        :busy-label="busyLabel"
        :operation-progress-percent="operationProgressPercent"
        :operation-progress-message="operationProgressMessage"
        :analysis-elapsed-label="analysisElapsedLabel"
        :use-cache="analysisUseCache"
        :expected-people-count="expectedPeopleCount"
        :hardware-summary="hardwareSummary"
        :hardware-profile="hardwareProfile"
        :allow-cpu-fallback="allowCpuFallback"
        :can-reanalyze-selected="selectedVideo !== null"
        :can-cancel-analysis="canCancelAnalysis"
        :pending-import-count="pendingImportCount"
        :analysis-jobs="analysisJobs"
        :active-analyze-job-id="analysisJob?.job_id ?? null"
        @update:use-cache="analysisUseCache = $event"
        @update:expected-people-count="expectedPeopleCount = $event"
        @update:hardware-profile="hardwareProfile = $event"
        @update:allow-cpu-fallback="allowCpuFallback = $event"
        @upload-files="processVideoFiles"
        @analyze-path="analyzeServerPath"
        @import-timeline="submitImportTimeline"
        @reanalyze-selected="reanalyzeSelectedVideo"
        @cancel-analysis="cancelCurrentAnalysis"
        @select-video="selectVideo"
        @trash-video="submitTrashVideo"
        @restore-video="submitRestoreVideo"
        @purge-video="submitPurgeVideo"
      />

      <section class="viewer-stack grid min-w-0 overflow-y-auto bg-[#080a0d]" :style="viewerStackStyle">
        <VideoMonitor
          ref="videoMonitorRef"
          :selected-video="selectedVideo"
          :face-box-enabled="faceBoxEnabled"
          :face-overlay-boxes="faceOverlayBoxes"
          :is-playing="isPlaying"
          :current-time="currentTime"
          :selected-person-label="selectedPersonLabel"
          :active-segment-label="activeSegmentLabel"
          :people-count="visiblePeople.length"
          :segments-count="segments.length"
          :tracks-count="tracks.length"
          :status-message="statusMessage"
          @toggle-face-box="toggleFaceBox"
          @content-changed="updateFaceOverlay"
          @time-update="syncCurrentTime"
          @playing-changed="isPlaying = $event"
          @playback-error="errorMessage = $event"
        />

        <div
          class="panel-resize-handle"
          role="separator"
          aria-label="调整视频窗口高度"
          aria-orientation="horizontal"
          tabindex="0"
          @keydown="handlePanelResizeKeydown('video', $event)"
          @pointerdown="startPanelResize('video', $event)"
        >
          <span class="panel-resize-grip" aria-hidden="true" />
        </div>

        <PeopleTimeline
          :people="timelinePeople"
          :segments="segments"
          :selected-person-id="selectedPersonId"
          :active-segment-id="activeSegmentId"
          :review-drop-target-person-id="personDropTargetId"
          :current-time="currentTime"
          :duration-seconds="selectedVideo?.duration_seconds ?? 0"
          @select-person="togglePersonSelection"
          @jump-to-segment="jumpToSegment"
          @seek-time="seekTimelineTime"
          @toggle-playback="togglePlaybackFromTimeline"
          @segment-drag-start="startTimelineSegmentDrag"
          @segment-drag-target="setTimelineSegmentDropTarget"
          @segment-drop="dropTimelineSegmentOnPerson"
          @segment-drag-end="finishTimelineSegmentDrag"
          @delete-person="confirmDeletePerson"
          @delete-segment="confirmDeleteSegment"
        />

        <div
          class="panel-resize-handle"
          role="separator"
          aria-label="调整人物出现时间轴高度"
          aria-orientation="horizontal"
          tabindex="0"
          @keydown="handlePanelResizeKeydown('timeline', $event)"
          @pointerdown="startPanelResize('timeline', $event)"
        >
          <span class="panel-resize-grip" aria-hidden="true" />
        </div>

        <WorkspaceReviewPanel
          :track-review-items="trackReviewItems"
          :review-card-size-options="reviewCardSizeOptions"
          :review-card-size="reviewCardSize"
          :review-grid-style="reviewGridStyle"
          :selected-review-track-ids="selectedReviewTrackIds"
          :review-drag-track-ids="reviewDragTrackIds"
          :selected-person-id="selectedPersonId"
          :review-selection-rect="reviewSelectionRect"
          :review-selection-rect-style="reviewSelectionRectStyle"
          v-model:bulk-target-person-id="bulkTargetPersonId"
          :visible-people="visiblePeople"
          :is-reviewing="isReviewing"
          :set-review-panel-ref="setReviewPanelRef"
          :set-review-viewport-ref="setReviewViewportRef"
          :set-review-grid-ref="setReviewGridRef"
          :set-review-card-ref="setReviewCardRef"
          :format-count="formatCount"
          :format-time="formatTime"
          @set-review-card-size="setReviewCardSize"
          @focus-review-panel="focusReviewPanel"
          @select-all-review-tracks="selectAllReviewTracks"
          @clear-review-selection="clearReviewSelection"
          @start-review-box-select="startReviewBoxSelect"
          @move-review-box-select="moveReviewBoxSelect"
          @finish-review-box-select="finishReviewBoxSelect"
          @toggle-review-track="toggleReviewTrack"
          @submit-bulk-assign="submitBulkAssign"
          @delete-selected-track-people="deleteSelectedTrackPeople"
        />
        <div
          class="panel-resize-handle panel-resize-handle--end"
          role="separator"
          aria-label="调整批量整理人脸高度"
          aria-orientation="horizontal"
          tabindex="0"
          @keydown="handlePanelResizeKeydown('review', $event)"
          @pointerdown="startPanelResize('review', $event)"
        >
          <span class="panel-resize-grip" aria-hidden="true" />
        </div>
      </section>

      <WorkspaceInspector
        :selected-person="selectedPerson"
        :selected-person-id="selectedPersonId"
        :selected-person-label="selectedPersonLabel"
        :visible-people-count="visiblePeople.length"
        :visible-segments-count="visibleSegments.length"
        :hidden-people-count="hiddenPeopleCount"
        :selected-video="selectedVideo"
        v-model:video-title-draft="videoTitleDraft"
        v-model:video-series-draft="videoSeriesDraft"
        v-model:video-source-path-draft="videoSourcePathDraft"
        v-model:person-query="personQuery"
        :filtered-people="filteredPeople"
        :segments-count="segments.length"
        :visible-segments="visibleSegments"
        :active-segment-id="activeSegmentId"
        :person-drop-target-id="personDropTargetId"
        :dragged-timeline-segment="draggedTimelineSegment"
        v-model:review-label="reviewLabel"
        v-model:global-person-target-id="globalPersonTargetId"
        v-model:new-global-person-label="newGlobalPersonLabel"
        :selected-global-person="selectedGlobalPerson"
        :global-people="globalPeople"
        :can-link-global="canLinkGlobal"
        :can-review-global="canReviewGlobal"
        :is-reviewing="isReviewing"
        :is-global-reviewing="isGlobalReviewing"
        :right-panel-style="rightPanelStyle"
        :right-panel-section-class="rightPanelSectionClass"
        :right-panel-body-class="rightPanelBodyClass"
        :start-right-panel-resize="startRightPanelResize"
        :handle-right-panel-resize-keydown="handleRightPanelResizeKeydown"
        :format-count="formatCount"
        :format-time="formatTime"
        :source-directory-from-path="sourceDirectoryFromPath"
        :global-person-label="globalPersonLabel"
        :person-name="personName"
        :is-hidden-person="isHiddenPerson"
        @select-person="selectPerson"
        @toggle-person-selection="togglePersonSelection"
        @confirm-delete-person="confirmDeletePerson"
        @timeline-segment-drag-over="handleTimelineSegmentDragOver"
        @drop-timeline-segment-on-person="dropTimelineSegmentOnPerson"
        @submit-video-metadata="submitVideoMetadata"
        @submit-rename="submitRename"
        @submit-toggle-person-hidden="submitTogglePersonHidden"
        @submit-delete="submitDelete"
        @submit-link-global="submitLinkGlobal"
        @submit-create-global-person="submitCreateGlobalPerson"
        @submit-confirm-global="submitConfirmGlobal"
        @submit-reject-global="submitRejectGlobal"
        @jump-to-segment="jumpToSegment"
        @play-segment="playSegment"
      />
    </section>

    <WorkspaceFeedbackOverlay
      :status-message="statusMessage"
      :error-message="errorMessage"
      :review-drag-preview="reviewDragPreview"
      :review-drag-preview-style="reviewDragPreviewStyle"
      :format-count="formatCount"
    />
	  </main>
	</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import {
  assignTracks,
  confirmGlobalObservation,
  createGlobalPersonFromLocal,
  deletePerson,
  deleteTracks,
  getVideo,
  importTimeline as importTimelineFile,
  linkPersonToGlobal,
  listGlobalPeople,
  listTrackDetections,
  listVideos,
  renamePerson,
  rejectGlobalObservation,
  setPersonHidden,
  purgeVideo,
  restoreVideo,
  trashVideo,
  updateVideo,
  type GlobalPersonItem,
  type SegmentItem,
  type TrackDetectionItem,
  type TrackItem,
  type VideoDetail,
  type VideoItem
} from "../api";
import MediaSidebar from "../components/workspace/MediaSidebar.vue";
import PeopleTimeline from "../components/workspace/PeopleTimeline.vue";
import VideoMonitor from "../components/workspace/VideoMonitor.vue";
import WorkspaceFeedbackOverlay from "../components/workspace/WorkspaceFeedbackOverlay.vue";
import WorkspaceHeader from "../components/workspace/WorkspaceHeader.vue";
import WorkspaceInspector from "../components/workspace/WorkspaceInspector.vue";
import WorkspaceReviewPanel from "../components/workspace/WorkspaceReviewPanel.vue";
import { buildFaceOverlayBoxes, type FaceOverlayBox } from "../components/workspace/faceOverlay";
import {
  clamp,
  formatCount,
  formatTime,
  globalPersonLabel,
  parseTrackIds,
  sourceDirectoryFromPath,
  videoDisplayTitle,
} from "../components/workspace/workspaceUtils";
import { useWorkspaceAnalysis, type PresetId } from "../composables/useWorkspaceAnalysis";
import { useWorkspacePanelResize } from "../composables/useWorkspacePanelResize";

/** 审阅卡片尺寸选项。 */
type ReviewCardSize = "small" | "medium" | "large";
/** 审阅轨迹拖拽时的浮层预览。 */
type ReviewDragPreview = {
  x: number;
  y: number;
  count: number;
  facePath: string | null;
};
/** 顶部栏可选择的分析预设。 */
const presets: Array<{ id: PresetId; label: string }> = [
  { id: "fast", label: "Fast" },
  { id: "balanced", label: "Balanced" },
  { id: "crowd", label: "Crowd" }
];
/** 审阅卡片尺寸的 localStorage key。 */
const reviewCardSizeStorageKey = "facetimemarker.workspace.reviewCardSize";
/** 当前帧人脸框匹配轨迹检测的容差秒数。 */
const frameDetectionToleranceSeconds = 0.8;
/** 播放片段时提前进入片段的秒数。 */
const segmentSeekLeadSeconds = 1.0;
/** 审阅卡片尺寸对应的最小宽度。 */
const reviewCardSizeOptions: Array<{ id: ReviewCardSize; label: string; minWidth: number }> = [
  { id: "small", label: "小", minWidth: 92 },
  { id: "medium", label: "中", minWidth: 118 },
  { id: "large", label: "大", minWidth: 150 },
];

const videos = ref<VideoItem[]>([]);
const trashVideos = ref<VideoItem[]>([]);
const detail = ref<VideoDetail | null>(null);
const trackDetections = ref<TrackDetectionItem[]>([]);
const selectedPersonId = ref<number | null>(null);
const personQuery = ref("");
const videoQuery = ref("");
const videoTitleDraft = ref("");
const videoSeriesDraft = ref("");
const videoSourcePathDraft = ref("");
const globalPersonTargetId = ref("");
const newGlobalPersonLabel = ref("");
const videoMonitorRef = ref<InstanceType<typeof VideoMonitor> | null>(null);
const reviewPanelEl = ref<HTMLElement | null>(null);
const reviewViewportEl = ref<HTMLElement | null>(null);
const reviewGridEl = ref<HTMLElement | null>(null);
const currentTime = ref(0);
const activeSegmentId = ref<number | null>(null);
const isPlaying = ref(false);
const isImporting = ref(false);
const isReviewing = ref(false);
const isGlobalReviewing = ref(false);
const statusMessage = ref("");
const errorMessage = ref("");
const reviewLabel = ref("");
const selectedReviewTrackIds = ref<number[]>([]);
const bulkTargetPersonId = ref<number | null>(null);
const reviewSelectionRect = ref<{
  startX: number;
  startY: number;
  currentX: number;
  currentY: number;
} | null>(null);
const isReviewBoxSelecting = ref(false);
const suppressNextReviewClick = ref(false);
const reviewDragTrackIds = ref<number[]>([]);
const reviewDragPreview = ref<ReviewDragPreview | null>(null);
const reviewDropTargetPersonId = ref<number | null>(null);
const draggedTimelineSegment = ref<SegmentItem | null>(null);
const timelineSegmentDropTargetPersonId = ref<number | null>(null);
const reviewPointerAction = ref<"idle" | "pending" | "selecting" | "dragging">("idle");
const reviewPointerStart = ref<{
  x: number;
  y: number;
  viewportX: number;
  viewportY: number;
  trackId: number | null;
} | null>(null);
const globalPeople = ref<GlobalPersonItem[]>([]);
const faceBoxEnabled = ref(true);
const highlightedTrackId = ref<number | null>(null);
const videoContentRect = ref<{ left: number; top: number; width: number; height: number } | null>(
  null
);
/** 面板尺寸组合函数提供的布局样式和拖拽事件处理器。 */
const {
  viewerStackStyle,
  focusReviewPanelHeight,
  rightPanelStyle,
  rightPanelSectionClass,
  rightPanelBodyClass,
  startPanelResize,
  stopPanelResize,
  handlePanelResizeKeydown,
  startRightPanelResize,
  stopRightPanelResize,
  handleRightPanelResizeKeydown,
} = useWorkspacePanelResize(() => window.requestAnimationFrame(updateFaceOverlay));
let statusTimer: number | undefined;
let elapsedTimer: number | undefined;
const reviewCardEls = new Map<number, HTMLElement>();

const {
  timelinePath,
  serverVideoPath,
  selectedPreset,
  analysisSeriesName,
  analysisConfigPath,
  analysisUseCache,
  expectedPeopleCount,
  hardwareSummary,
  hardwareProfile,
  allowCpuFallback,
  isUploading,
  isAnalyzing,
  analysisJob,
  analysisJobs,
  elapsedNow,
  pendingImportCount,
  canCancelAnalysis,
  busyLabel,
  operationProgressPercent,
  operationProgressMessage,
  analysisElapsedLabel,
  refreshHardware,
  refreshAnalysisJobs,
  restoreLatestActiveAnalysisJob,
  processVideoFiles,
  analyzeServerPath,
  reanalyzeSelectedVideo,
  cancelCurrentAnalysis,
} = useWorkspaceAnalysis({
  detail,
  statusMessage,
  errorMessage,
  isImporting,
  refreshAll,
  selectVideo,
});

/** 当前审阅卡片尺寸。 */
const reviewCardSize = ref<ReviewCardSize>(loadReviewCardSize());
/** 将卡片尺寸选项转换为网格 CSS 变量。 */
const reviewGridStyle = computed(() => {
  const option =
    reviewCardSizeOptions.find((item) => item.id === reviewCardSize.value) ??
    reviewCardSizeOptions[1];
  return {
    "--review-card-min": `${option.minWidth}px`,
  };
});
/** 计算审阅拖拽预览浮层位置。 */
const reviewDragPreviewStyle = computed(() => {
  const preview = reviewDragPreview.value;
  if (!preview) return {};
  return {
    left: `${preview.x + 16}px`,
    top: `${preview.y + 16}px`,
  };
});
/** 当前已载入的视频详情。 */
const selectedVideo = computed(() => detail.value);
/** 当前视频的人物列表。 */
const people = computed(() => detail.value?.people ?? []);
/** 当前视频中被隐藏的人物数量。 */
const hiddenPeopleCount = computed(() => people.value.filter(isHiddenPerson).length);
/** 按隐藏状态和人物 ID 排序后的人物列表。 */
const visiblePeople = computed(() => {
  return [...people.value].sort((a, b) => {
    const hiddenDelta = Number(isHiddenPerson(a)) - Number(isHiddenPerson(b));
    return hiddenDelta || a.person_id - b.person_id;
  });
});
/** 可见人物 ID 集合，用于过滤片段和轨迹。 */
const visiblePersonIds = computed(() => new Set(visiblePeople.value.map((person) => person.person_id)));
/** 当前视频的时间轴片段。 */
const segments = computed(() => detail.value?.segments ?? []);
/** 当前视频的人脸轨迹。 */
const tracks = computed(() => detail.value?.tracks ?? []);
/** 工作台是否处于上传、分析或导入忙碌状态。 */
const isBusy = computed(() => isUploading.value || isAnalyzing.value || isImporting.value);
/** 当前选中的人物。 */
const selectedPerson = computed(() => {
  if (selectedPersonId.value === null) return null;
  return people.value.find((person) => person.person_id === selectedPersonId.value) ?? null;
});
/** 当前人物关联的全局人物档案。 */
const selectedGlobalPerson = computed(() => {
  const globalPersonId = selectedPerson.value?.global_person_id;
  if (!globalPersonId) return null;
  return globalPeople.value.find((person) => person.global_person_id === globalPersonId) ?? null;
});
/** 当前人物是否可执行全局档案确认或驳回。 */
const canReviewGlobal = computed(() => {
  return Boolean(detail.value?.path && selectedPerson.value?.global_person_id);
});
/** 当前人物是否可关联到已有全局档案。 */
const canLinkGlobal = computed(() => {
  return Boolean(detail.value && selectedPerson.value && globalPersonTargetId.value.trim());
});
/** 审阅卡片或时间轴拖拽时共同使用的人物投放目标。 */
const personDropTargetId = computed(
  () => reviewDropTargetPersonId.value ?? timelineSegmentDropTargetPersonId.value,
);
/** 当前人物选择的展示标签。 */
const selectedPersonLabel = computed(() => selectedPerson.value?.label ?? "全部人物");
/** 当前定位片段的展示标签。 */
const activeSegmentLabel = computed(() => {
  const segment = segments.value.find((item) => item.id === activeSegmentId.value);
  if (!segment) return "未定位片段";
  return `${personName(segment.person_id)} ${formatTime(segment.start)}`;
});
/** 当前过滤条件下可见的时间轴片段。 */
const visibleSegments = computed(() => {
  const nextSegments =
    selectedPersonId.value === null
      ? segments.value.filter((segment) => visiblePersonIds.value.has(segment.person_id))
      : segments.value.filter((segment) => segment.person_id === selectedPersonId.value);
  return [...nextSegments].sort((a, b) => a.start - b.start);
});
/** 时间轴需要展示的人物列表。 */
const timelinePeople = computed(() => {
  return visiblePeople.value;
});
/** 右侧人物列表搜索后的结果。 */
const filteredPeople = computed(() => {
  const query = personQuery.value.trim().toLowerCase();
  if (!query) return visiblePeople.value;
  return visiblePeople.value.filter((person) => {
    return (
      person.label.toLowerCase().includes(query) ||
      (person.global_person_id ?? "").toLowerCase().includes(query)
    );
  });
});
/** 审阅区按人物和开始时间排序后的轨迹卡片。 */
const trackReviewItems = computed(() => {
  return tracks.value
    .filter((track) => track.track_id !== null)
    .filter((track) => track.person_id === null || visiblePersonIds.value.has(track.person_id))
    .map((track) => ({
      track,
      personLabel: personName(track.person_id ?? -1),
      facePath: track.representative_face_path ?? representativeFaceForTrack(track),
    }))
    .sort((a, b) => {
      const personDelta = (a.track.person_id ?? -1) - (b.track.person_id ?? -1);
      if (personDelta !== 0) return personDelta;
      return a.track.start - b.track.start;
    });
});
/** 当前高亮轨迹或当前片段的首条轨迹。 */
const highlightedTrack = computed(() => {
  if (highlightedTrackId.value !== null) {
    const selectedTrack = tracks.value.find((track) => track.track_id === highlightedTrackId.value);
    if (selectedTrack) return selectedTrack;
  }
  const activeSegment = segments.value.find((segment) => segment.id === activeSegmentId.value);
  return firstTrackForSegment(activeSegment ?? null);
});
/** 当前视频画面上应绘制的人脸框。 */
const faceOverlayBoxes = computed<FaceOverlayBox[]>(() => {
  return buildFaceOverlayBoxes({
    enabled: faceBoxEnabled.value,
    video: selectedVideo.value,
    contentRect: videoContentRect.value,
    tracks: tracks.value,
    detections: trackDetections.value,
    currentTime: currentTime.value,
    visiblePersonIds: visiblePersonIds.value,
    highlightedTrack: highlightedTrack.value,
    personName,
    toleranceSeconds: frameDetectionToleranceSeconds,
  });
});
/** 审阅框选矩形的绝对定位样式。 */
const reviewSelectionRectStyle = computed(() => {
  const rect = reviewSelectionRect.value;
  if (!rect) return {};
  const left = Math.min(rect.startX, rect.currentX);
  const top = Math.min(rect.startY, rect.currentY);
  const width = Math.abs(rect.currentX - rect.startX);
  const height = Math.abs(rect.currentY - rect.startY);
  return {
    left: `${left}px`,
    top: `${top}px`,
    width: `${width}px`,
    height: `${height}px`,
  };
});
/** 同步选中人物到右侧审阅表单。 */
watch(selectedPerson, (person) => {
  reviewLabel.value = person?.label ?? "";
  globalPersonTargetId.value = person?.global_person_id ?? "";
  newGlobalPersonLabel.value = person?.label ?? "";
  if (person?.person_id !== bulkTargetPersonId.value) {
    bulkTargetPersonId.value = person?.person_id ?? null;
  }
});

/** 同步选中视频到作品元数据表单。 */
watch(selectedVideo, (video) => {
  videoTitleDraft.value = videoDisplayTitle(video);
  videoSeriesDraft.value = video?.series_name ?? "";
  videoSourcePathDraft.value = video?.source_path || video?.path || "";
});

/** 非忙碌状态下自动清理状态消息。 */
watch(statusMessage, (message) => {
  window.clearTimeout(statusTimer);
  if (message && !isBusy.value) {
    statusTimer = window.setTimeout(() => {
      statusMessage.value = "";
    }, 2400);
  }
});

/** 忙碌状态结束后延迟清理状态消息。 */
watch(isBusy, (busy) => {
  window.clearTimeout(statusTimer);
  if (!busy && statusMessage.value) {
    statusTimer = window.setTimeout(() => {
      statusMessage.value = "";
    }, 2400);
  }
});

/** 页面挂载后加载初始数据并恢复后台任务。 */
onMounted(async () => {
  window.addEventListener("resize", updateFaceOverlay);
  elapsedTimer = window.setInterval(() => {
    elapsedNow.value = Date.now();
  }, 1000);
  await refreshAll();
  if (videos.value[0]) {
    await selectVideo(videos.value[0].id);
  }
  void restoreLatestActiveAnalysisJob();
});

/** 页面卸载时移除全局监听和定时器。 */
onBeforeUnmount(() => {
  window.removeEventListener("resize", updateFaceOverlay);
  stopPanelResize();
  stopRightPanelResize();
  window.clearTimeout(statusTimer);
  window.clearInterval(elapsedTimer);
});

/** 刷新工作台依赖的所有基础数据。 */
async function refreshAll() {
  await refreshVideos();
  await refreshGlobalPeople();
  await refreshHardware();
  await refreshAnalysisJobs();
}

/** 刷新素材列表和回收站列表。 */
async function refreshVideos() {
  try {
    errorMessage.value = "";
    const allVideos = await listVideos({ includeDeleted: true });
    videos.value = allVideos.filter((video) => !video.deleted_at);
    trashVideos.value = allVideos.filter((video) => Boolean(video.deleted_at));
    statusMessage.value = "视频列表已刷新";
  } catch {
    errorMessage.value = "无法读取视频列表，请确认后端服务已经启动。";
  }
}

/** 刷新全局人物档案列表。 */
async function refreshGlobalPeople() {
  try {
    globalPeople.value = await listGlobalPeople();
  } catch {
    globalPeople.value = [];
  }
}

/** 加载指定视频详情并重置播放和审阅选择。 */
async function selectVideo(id: number) {
  try {
    errorMessage.value = "";
    detail.value = await getVideo(id);
    try {
      trackDetections.value = await listTrackDetections(id);
    } catch {
      trackDetections.value = [];
    }
	    const firstPerson =
	      detail.value.people.find((person) => !isHiddenPerson(person)) ??
	      detail.value.people[0] ??
	      null;
	    selectedPersonId.value = firstPerson?.person_id ?? null;
    activeSegmentId.value = null;
    highlightedTrackId.value = null;
    videoContentRect.value = null;
    currentTime.value = 0;
    selectedReviewTrackIds.value = [];
    bulkTargetPersonId.value = null;
    statusMessage.value = "视频已载入";
  } catch {
    trackDetections.value = [];
    errorMessage.value = "无法读取视频详情，请重新刷新列表。";
  }
}

/** 导入 timeline.json 并打开生成的视频详情。 */
async function submitImportTimeline() {
  isImporting.value = true;
  errorMessage.value = "";
  try {
    statusMessage.value = "正在导入时间轴";
    const payload = await importTimelineFile(timelinePath.value.trim());
    await refreshAll();
    await selectVideo(payload.video_id);
    statusMessage.value = "时间轴已导入";
  } catch {
    errorMessage.value = "导入失败，请检查 timeline.json 路径是否存在。";
  } finally {
    isImporting.value = false;
  }
}

/** 将素材移入回收站并处理当前选中状态。 */
async function submitTrashVideo(videoId: number) {
  try {
    errorMessage.value = "";
    const wasSelected = detail.value?.id === videoId;
    await trashVideo(videoId);
    await refreshVideos();
    if (wasSelected) {
      detail.value = null;
      trackDetections.value = [];
      selectedPersonId.value = null;
      activeSegmentId.value = null;
      highlightedTrackId.value = null;
      currentTime.value = 0;
      if (videos.value[0]) {
        await selectVideo(videos.value[0].id);
      }
    }
    await refreshGlobalPeople();
    statusMessage.value = "素材已移入回收站";
  } catch {
    errorMessage.value = "素材移入回收站失败，请刷新后重试。";
  }
}

/** 从回收站恢复素材并打开它。 */
async function submitRestoreVideo(videoId: number) {
  try {
    errorMessage.value = "";
    const restored = await restoreVideo(videoId);
    await refreshVideos();
    await refreshGlobalPeople();
    await selectVideo(restored.id);
    statusMessage.value = "素材已还原";
  } catch {
    errorMessage.value = "素材还原失败，请刷新后重试。";
  }
}

/** 确认后彻底删除素材分析数据。 */
async function submitPurgeVideo(videoId: number) {
  if (!window.confirm("彻底删除会移除这个素材的分析数据，源视频文件不会删除。继续？")) {
    return;
  }
  try {
    errorMessage.value = "";
    await purgeVideo(videoId);
    await refreshVideos();
    await refreshGlobalPeople();
    statusMessage.value = "素材数据已彻底删除";
  } catch {
    errorMessage.value = "彻底删除失败，请刷新后重试。";
  }
}

/** 从本地存储读取审阅卡片尺寸。 */
function loadReviewCardSize(): ReviewCardSize {
  try {
    const raw = window.localStorage.getItem(reviewCardSizeStorageKey);
    return raw === "small" || raw === "medium" || raw === "large" ? raw : "medium";
  } catch {
    return "medium";
  }
}

/** 设置并持久化审阅卡片尺寸。 */
function setReviewCardSize(size: ReviewCardSize) {
  reviewCardSize.value = size;
  try {
    window.localStorage.setItem(reviewCardSizeStorageKey, size);
  } catch {
    return;
  }
}

/** 收起上方面板并滚动到审阅区。 */
function focusReviewPanel() {
  focusReviewPanelHeight();
  window.requestAnimationFrame(() => {
    reviewPanelEl.value?.scrollIntoView({ block: "start", behavior: "smooth" });
    updateFaceOverlay();
  });
}

/** 直接设置当前选中人物，并优先定位到人物代表头像对应帧。 */
async function selectPerson(personId: number | null) {
  selectedPersonId.value = personId;
  if (personId !== null) {
    await seekPersonRepresentativeFrame(personId);
  }
}

/** 切换右侧人物列表中的当前选择。 */
async function togglePersonSelection(personId: number) {
  if (selectedPersonId.value === personId) {
    selectedPersonId.value = null;
    return;
  }
  selectedPersonId.value = personId;
  await seekPersonRepresentativeFrame(personId);
}

/** 定位到人物代表头像实际来自的检测帧。 */
async function seekPersonRepresentativeFrame(personId: number) {
  const person = people.value.find((item) => item.person_id === personId);
  const timestamp = person?.representative_timestamp;
  if (typeof timestamp !== "number" || !Number.isFinite(timestamp)) return;
  await seekTimelineTime(timestamp);
  statusMessage.value = `已定位到 ${personName(personId)} 头像帧 ${formatTime(timestamp)}`;
}

/** 切换审阅轨迹卡片的选中状态并定位视频。 */
function toggleReviewTrack(trackId: number, track?: TrackItem) {
  if (isReviewBoxSelecting.value) return;
  if (suppressNextReviewClick.value) {
    return;
  }
  highlightedTrackId.value = track?.track_id ?? trackId;
  if (track) {
    jumpToTrack(track);
  }
  if (selectedReviewTrackIds.value.includes(trackId)) {
    selectedReviewTrackIds.value = selectedReviewTrackIds.value.filter((id) => id !== trackId);
    return;
  }
  selectedReviewTrackIds.value = [...selectedReviewTrackIds.value, trackId];
}

/** 选中当前审阅区全部轨迹。 */
function selectAllReviewTracks() {
  selectedReviewTrackIds.value = trackReviewItems.value.map((item) => item.track.track_id);
}

/** 清空审阅轨迹选择。 */
function clearReviewSelection() {
  selectedReviewTrackIds.value = [];
}

/** 在拖拽或框选结束后吞掉下一次点击。 */
function suppressReviewClickOnce() {
  suppressNextReviewClick.value = true;
  window.setTimeout(() => {
    suppressNextReviewClick.value = false;
  }, 0);
}

/** 更新审阅轨迹拖拽浮层的位置和缩略图。 */
function updateReviewDragPreview(event: PointerEvent, trackIds: number[]) {
  const firstTrackId = trackIds[0];
  const firstItem = trackReviewItems.value.find((item) => item.track.track_id === firstTrackId);
  reviewDragPreview.value = {
    x: event.clientX,
    y: event.clientY,
    count: trackIds.length,
    facePath: firstItem?.facePath ?? null,
  };
}

/** 接收批量整理面板 DOM 引用，用于聚焦滚动。 */
function setReviewPanelRef(el: unknown) {
  reviewPanelEl.value = el instanceof HTMLElement ? el : null;
}

/** 接收批量整理滚动容器 DOM 引用，用于框选坐标换算。 */
function setReviewViewportRef(el: unknown) {
  reviewViewportEl.value = el instanceof HTMLElement ? el : null;
}

/** 接收批量整理网格 DOM 引用，保留给后续布局测量。 */
function setReviewGridRef(el: unknown) {
  reviewGridEl.value = el instanceof HTMLElement ? el : null;
}

/** 维护轨迹卡片 DOM 引用以支持框选命中。 */
function setReviewCardRef(el: unknown, trackId: number) {
  if (el instanceof HTMLElement) {
    reviewCardEls.set(trackId, el);
  } else {
    reviewCardEls.delete(trackId);
  }
}

/** 判断指针事件是否来自轨迹拖拽手柄。 */
function isReviewDragHandleEvent(target: Element) {
  return Boolean(target.closest("[data-review-drag-handle='true']"));
}

/** 开始审阅区框选或轨迹拖拽判定。 */
function startReviewBoxSelect(event: PointerEvent) {
  if (event.button !== 0 || !(event.target instanceof Element)) return;
  const viewport = reviewViewportEl.value;
  if (!viewport) return;
  const target = event.target.closest("[data-track-id]");
  if (target && !isReviewDragHandleEvent(event.target)) return;
  const trackId = target instanceof HTMLElement ? Number(target.dataset.trackId) : null;
  const point = pointerPointInViewport(event, viewport);
  const finiteTrackId = trackId !== null && Number.isFinite(trackId) ? trackId : null;
  reviewPointerAction.value = "pending";
  reviewPointerStart.value = {
    x: event.clientX,
    y: event.clientY,
    viewportX: point.x,
    viewportY: point.y,
    trackId: finiteTrackId,
  };
  isReviewBoxSelecting.value = false;
  suppressNextReviewClick.value = false;
  reviewViewportEl.value?.setPointerCapture(event.pointerId);
}

/** 更新审阅区框选矩形或拖拽浮层。 */
function moveReviewBoxSelect(event: PointerEvent) {
  if (reviewPointerAction.value === "idle" || !reviewPointerStart.value || !reviewViewportEl.value) {
    return;
  }
  const point = pointerPointInViewport(event, reviewViewportEl.value);
	  if (reviewPointerAction.value === "pending") {
	    const moved = Math.hypot(
	      event.clientX - reviewPointerStart.value.x,
	      event.clientY - reviewPointerStart.value.y,
	    );
	    if (moved < 6) return;
	    event.preventDefault();

	    const trackId = reviewPointerStart.value.trackId;
	    if (trackId !== null) {
	      reviewPointerAction.value = "dragging";
	      const shouldDragSelection =
	        selectedReviewTrackIds.value.includes(trackId) && selectedReviewTrackIds.value.length > 1;
	      const nextDragIds = shouldDragSelection ? [...selectedReviewTrackIds.value] : [trackId];
	      selectedReviewTrackIds.value = nextDragIds;
	      reviewDragTrackIds.value = nextDragIds;
	      updateReviewDragPreview(event, nextDragIds);
	      updateReviewDropTarget(event);
	      return;
	    }

    reviewPointerAction.value = "selecting";
    isReviewBoxSelecting.value = true;
    reviewSelectionRect.value = {
      startX: reviewPointerStart.value.viewportX,
      startY: reviewPointerStart.value.viewportY,
      currentX: point.x,
      currentY: point.y,
    };
  }

	  if (reviewPointerAction.value === "dragging") {
	    event.preventDefault();
	    updateReviewDragPreview(event, reviewDragTrackIds.value);
	    updateReviewDropTarget(event);
	    return;
	  }

	  if (reviewPointerAction.value !== "selecting" || !reviewSelectionRect.value) return;
	  event.preventDefault();
	  reviewSelectionRect.value = {
    ...reviewSelectionRect.value,
    currentX: point.x,
    currentY: point.y,
  };
  if (hasReviewSelectionArea(reviewSelectionRect.value)) {
    selectedReviewTrackIds.value = trackIdsInsideReviewSelection();
  }
}

/** 结束审阅区框选或拖拽并执行投放。 */
function finishReviewBoxSelect(event: PointerEvent) {
  if (reviewPointerAction.value === "idle") return;
  moveReviewBoxSelect(event);
	  const wasDragging = reviewPointerAction.value === "dragging";
	  const hadSelectionArea = reviewPointerAction.value === "selecting" && hasReviewSelectionArea(reviewSelectionRect.value);
	  if (wasDragging && reviewDropTargetPersonId.value !== null) {
	    void dropReviewTracksOnPerson(reviewDropTargetPersonId.value);
	  }
  reviewPointerAction.value = "idle";
  reviewPointerStart.value = null;
	  isReviewBoxSelecting.value = false;
	  reviewSelectionRect.value = null;
	  if (hadSelectionArea || wasDragging) {
	    suppressReviewClickOnce();
	  }
	  if (!wasDragging) {
	    reviewDragTrackIds.value = [];
	    reviewDragPreview.value = null;
	    reviewDropTargetPersonId.value = null;
	  } else if (reviewDropTargetPersonId.value === null) {
	    finishReviewDrag();
	  }
  try {
    reviewViewportEl.value?.releasePointerCapture(event.pointerId);
  } catch {
    // Pointer capture can already be released by the browser.
  }
}

/** 将指针坐标转换成审阅滚动容器内坐标。 */
function pointerPointInViewport(event: PointerEvent, viewport: HTMLElement) {
  const rect = viewport.getBoundingClientRect();
  return {
    x: event.clientX - rect.left + viewport.scrollLeft,
    y: event.clientY - rect.top + viewport.scrollTop,
  };
}

/** 计算当前框选矩形命中的轨迹 ID。 */
function trackIdsInsideReviewSelection() {
  const viewport = reviewViewportEl.value;
  const selection = reviewSelectionRect.value;
  if (!viewport || !selection) return [];
  const viewportRect = viewport.getBoundingClientRect();
  const left = Math.min(selection.startX, selection.currentX);
  const top = Math.min(selection.startY, selection.currentY);
  const right = Math.max(selection.startX, selection.currentX);
  const bottom = Math.max(selection.startY, selection.currentY);
  if (right - left < 6 || bottom - top < 6) return [];

  const selected: number[] = [];
  for (const [trackId, element] of reviewCardEls.entries()) {
    const rect = element.getBoundingClientRect();
    const card = {
      left: rect.left - viewportRect.left + viewport.scrollLeft,
      top: rect.top - viewportRect.top + viewport.scrollTop,
      right: rect.right - viewportRect.left + viewport.scrollLeft,
      bottom: rect.bottom - viewportRect.top + viewport.scrollTop,
    };
    if (rectsIntersect({ left, top, right, bottom }, card)) {
      selected.push(trackId);
    }
  }
  return selected.sort((a, b) => a - b);
}

/** 判断框选矩形是否达到有效选择面积。 */
function hasReviewSelectionArea(
  rect: { startX: number; startY: number; currentX: number; currentY: number } | null,
) {
  if (!rect) return false;
  return Math.abs(rect.currentX - rect.startX) >= 6 && Math.abs(rect.currentY - rect.startY) >= 6;
}

/** 判断两个矩形是否相交。 */
function rectsIntersect(
  a: { left: number; top: number; right: number; bottom: number },
  b: { left: number; top: number; right: number; bottom: number },
) {
  return a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
}

/** 清理审阅轨迹拖拽状态。 */
function finishReviewDrag() {
  reviewDragTrackIds.value = [];
  reviewDragPreview.value = null;
  reviewDropTargetPersonId.value = null;
  reviewPointerAction.value = "idle";
  reviewPointerStart.value = null;
}

/** 根据指针所在元素更新审阅拖拽投放目标。 */
function updateReviewDropTarget(event: PointerEvent) {
  const target = document
    .elementFromPoint(event.clientX, event.clientY)
    ?.closest("[data-person-drop-id]");
  if (!(target instanceof HTMLElement)) {
    reviewDropTargetPersonId.value = null;
    return;
  }
  const personId = Number(target.dataset.personDropId);
  reviewDropTargetPersonId.value = Number.isFinite(personId) ? personId : null;
}

/** 将拖拽的审阅轨迹投放到目标人物。 */
async function dropReviewTracksOnPerson(personId: number) {
  if (reviewDragTrackIds.value.length === 0) return;
  const trackIds = [...reviewDragTrackIds.value];
  selectedReviewTrackIds.value = trackIds;
  bulkTargetPersonId.value = personId;
  finishReviewDrag();
  await assignSelectedTracksToPerson(personId);
}

/** 记录时间轴片段拖拽的起始片段。 */
function startTimelineSegmentDrag(segment: SegmentItem) {
  draggedTimelineSegment.value = segment;
  timelineSegmentDropTargetPersonId.value = null;
}

/** 设置时间轴片段拖拽的投放目标。 */
function setTimelineSegmentDropTarget(personId: number | null) {
  timelineSegmentDropTargetPersonId.value = personId;
}

/** 更新时间轴片段拖过的人物目标。 */
function handleTimelineSegmentDragOver(personId: number) {
  const segment = draggedTimelineSegment.value;
  timelineSegmentDropTargetPersonId.value =
    segment && segment.person_id !== personId ? personId : null;
}

/** 清理时间轴片段拖拽状态。 */
function finishTimelineSegmentDrag() {
  draggedTimelineSegment.value = null;
  timelineSegmentDropTargetPersonId.value = null;
}

/** 将时间轴片段中的轨迹移动到目标人物。 */
async function dropTimelineSegmentOnPerson(segment: SegmentItem | null, targetPersonId: number) {
  if (!segment || segment.person_id === targetPersonId) {
    finishTimelineSegmentDrag();
    return;
  }
  const trackIds = parseTrackIds(segment.track_ids);
  if (trackIds.length === 0) {
    statusMessage.value = "这个片段没有可移动的轨迹";
    finishTimelineSegmentDrag();
    return;
  }
  const videoId = detail.value?.id;
  if (!videoId) {
    finishTimelineSegmentDrag();
    return;
  }
  finishTimelineSegmentDrag();
  await runReviewAction(async () => {
    detail.value = await assignTracks(videoId, trackIds, targetPersonId);
    selectedPersonId.value = targetPersonId;
    selectedReviewTrackIds.value = [];
    bulkTargetPersonId.value = targetPersonId;
    const movedSegment = segments.value.find((item) =>
      parseTrackIds(item.track_ids).some((trackId) => trackIds.includes(trackId)),
    );
    activeSegmentId.value = movedSegment?.id ?? null;
    highlightedTrackId.value = trackIds[0] ?? null;
    await refreshVideos();
    statusMessage.value = `片段已归类到 ${personName(targetPersonId)}`;
  });
}

/** 开关视频画面上的人脸框覆盖层。 */
function toggleFaceBox() {
  faceBoxEnabled.value = !faceBoxEnabled.value;
  updateFaceOverlay();
}

/** 提交审阅区批量归类到目标人物。 */
async function submitBulkAssign() {
  if (!detail.value || bulkTargetPersonId.value === null || selectedReviewTrackIds.value.length === 0) {
    return;
  }
  await assignSelectedTracksToPerson(bulkTargetPersonId.value);
}

/** 将当前选中的轨迹归类到指定人物。 */
async function assignSelectedTracksToPerson(targetId: number) {
  if (!detail.value || selectedReviewTrackIds.value.length === 0) {
    return;
  }
  const videoId = detail.value.id;
  const trackIds = [...selectedReviewTrackIds.value];
  await runReviewAction(async () => {
    detail.value = await assignTracks(videoId, trackIds, targetId);
    selectedPersonId.value = targetId;
    selectedReviewTrackIds.value = [];
    statusMessage.value = `已归类 ${formatCount(trackIds.length)} 条轨迹`;
  });
}

/** 删除当前选中轨迹所属的人物。 */
async function deleteSelectedTrackPeople() {
  if (!detail.value || selectedReviewTrackIds.value.length === 0) return;
  const peopleToDelete = [
    ...new Set(
      tracks.value
        .filter((track) => selectedReviewTrackIds.value.includes(track.track_id))
        .map((track) => track.person_id)
        .filter((personId): personId is number => personId !== null)
    ),
  ];
  if (peopleToDelete.length === 0) return;
  if (
    !window.confirm(
      `将删除 ${formatCount(peopleToDelete.length)} 个人物及其轨迹、片段和截图。这个操作不可撤销，继续？`,
    )
  ) {
    return;
  }
  const videoId = detail.value.id;
  await runReviewAction(async () => {
    let nextDetail: VideoDetail | null = detail.value;
    for (const personId of peopleToDelete) {
      nextDetail = await deletePerson(videoId, personId);
    }
    detail.value = nextDetail;
    selectedPersonId.value = null;
    selectedReviewTrackIds.value = [];
    activeSegmentId.value = null;
    highlightedTrackId.value = null;
    statusMessage.value = `已删除 ${formatCount(peopleToDelete.length)} 个人物`;
  });
}

/** 确认后删除指定人物及其轨迹数据。 */
async function confirmDeletePerson(personId: number) {
  if (!detail.value) return;
  const label = personName(personId);
  if (!window.confirm(`将删除「${label}」及其所有轨迹、片段和截图。这个操作不可撤销，继续？`)) {
    return;
  }
  const videoId = detail.value.id;
  await runReviewAction(async () => {
    detail.value = await deletePerson(videoId, personId);
    if (selectedPersonId.value === personId) selectedPersonId.value = null;
    activeSegmentId.value = null;
    highlightedTrackId.value = null;
    selectedReviewTrackIds.value = [];
    statusMessage.value = `已删除 ${label}`;
  });
}

/** 确认后删除指定时间轴片段的轨迹。 */
async function confirmDeleteSegment(segment: SegmentItem) {
  if (!detail.value) return;
  const trackIds = parseTrackIds(segment.track_ids);
  if (trackIds.length === 0) {
    statusMessage.value = "这个片段没有可删除的轨迹";
    return;
  }
  if (
    !window.confirm(
      `将删除 ${personName(segment.person_id)} 在 ${formatTime(segment.start)} - ${formatTime(segment.end)} 的 ${formatCount(trackIds.length)} 条轨迹。这个操作不可撤销，继续？`,
    )
  ) {
    return;
  }
  const videoId = detail.value.id;
  await runReviewAction(async () => {
    detail.value = await deleteTracks(videoId, trackIds);
    activeSegmentId.value = null;
    highlightedTrackId.value = null;
    selectedReviewTrackIds.value = selectedReviewTrackIds.value.filter(
      (trackId) => !trackIds.includes(trackId),
    );
    statusMessage.value = "误检片段已删除";
  });
}

/** 提交当前人物的新名称。 */
async function submitRename() {
  if (!detail.value || selectedPersonId.value === null) return;
  const videoId = detail.value.id;
  const personId = selectedPersonId.value;
  const label = reviewLabel.value;
  await runReviewAction(async () => {
    detail.value = await renamePerson(videoId, personId, label);
    statusMessage.value = "人物名称已更新";
  });
}

/** 切换当前人物的隐藏状态。 */
async function submitTogglePersonHidden() {
  if (!detail.value || selectedPersonId.value === null || !selectedPerson.value) return;
  const videoId = detail.value.id;
  const personId = selectedPersonId.value;
  const nextHidden = !isHiddenPerson(selectedPerson.value);
  await runReviewAction(async () => {
    detail.value = await setPersonHidden(videoId, personId, nextHidden);
    selectedReviewTrackIds.value = [];
    await refreshVideos();
    await refreshGlobalPeople();
    statusMessage.value = nextHidden ? "人物已隐藏" : "人物已恢复显示";
  });
}

/** 保存当前作品的标题、系列和来源路径。 */
async function submitVideoMetadata() {
  if (!detail.value) return;
  const videoId = detail.value.id;
  await runReviewAction(async () => {
    const updated = await updateVideo(videoId, {
      title: videoTitleDraft.value,
      series_name: videoSeriesDraft.value,
      source_path: videoSourcePathDraft.value,
    });
    if (detail.value?.id === videoId) {
      detail.value = {
        ...detail.value,
        ...updated,
      };
    }
    await refreshVideos();
    statusMessage.value = "作品信息已保存";
  });
}

/** 删除当前选中的人物。 */
async function submitDelete() {
  if (!detail.value || selectedPersonId.value === null) return;
  await confirmDeletePerson(selectedPersonId.value);
}

/** 将当前人物关联到已有全局人物档案。 */
async function submitLinkGlobal() {
  if (!detail.value || selectedPersonId.value === null || !globalPersonTargetId.value.trim()) {
    return;
  }
  const videoId = detail.value.id;
  const personId = selectedPersonId.value;
  const targetGlobalPersonId = globalPersonTargetId.value.trim();
  await runGlobalReviewAction(async () => {
    detail.value = await linkPersonToGlobal(videoId, personId, targetGlobalPersonId);
    await refreshGlobalPeople();
    statusMessage.value = "人物档案已关联";
  });
}

/** 基于当前人物创建新的全局人物档案。 */
async function submitCreateGlobalPerson() {
  if (!detail.value || selectedPersonId.value === null) return;
  const videoId = detail.value.id;
  const personId = selectedPersonId.value;
  const label = newGlobalPersonLabel.value.trim() || reviewLabel.value.trim() || null;
  await runGlobalReviewAction(async () => {
    const nextDetail = await createGlobalPersonFromLocal(videoId, personId, label);
    detail.value = nextDetail;
    globalPersonTargetId.value = nextDetail.global_person_id;
    await refreshGlobalPeople();
    statusMessage.value = "人物档案已新建并关联";
  });
}

/** 确认当前人物属于已关联的全局人物档案。 */
async function submitConfirmGlobal() {
  if (!detail.value || !selectedPerson.value?.global_person_id) return;
  const globalPersonId = selectedPerson.value.global_person_id;
  const videoPath = detail.value.path;
  const localPersonId = selectedPerson.value.person_id;
  await runGlobalReviewAction(async () => {
    await confirmGlobalObservation(globalPersonId, videoPath, localPersonId);
    await refreshGlobalPeople();
    statusMessage.value = "人物档案匹配已确认";
  });
}

/** 驳回当前人物的全局档案关联。 */
async function submitRejectGlobal() {
  if (!detail.value || !selectedPerson.value?.global_person_id) return;
  const globalPersonId = selectedPerson.value.global_person_id;
  const videoId = detail.value.id;
  const videoPath = detail.value.path;
  const localPersonId = selectedPerson.value.person_id;
  await runGlobalReviewAction(async () => {
    await rejectGlobalObservation(globalPersonId, videoPath, localPersonId);
    await refreshGlobalPeople();
    detail.value = await getVideo(videoId);
    statusMessage.value = "已拆成新人物档案";
  });
}

/** 包装全局档案操作的 loading 和错误处理。 */
async function runGlobalReviewAction(action: () => Promise<void>) {
  isGlobalReviewing.value = true;
  errorMessage.value = "";
  try {
    await action();
  } catch {
    errorMessage.value = "人物档案操作失败，请刷新后重试。";
  } finally {
    isGlobalReviewing.value = false;
  }
}

/** 包装本地审阅操作的 loading 和错误处理。 */
async function runReviewAction(action: () => Promise<void>) {
  isReviewing.value = true;
  errorMessage.value = "";
  try {
    await action();
  } catch {
    errorMessage.value = "审阅操作失败，请刷新后重试。";
  } finally {
    isReviewing.value = false;
  }
}

/** 定位到片段起点并暂停视频。 */
async function jumpToSegment(segment: SegmentItem) {
  const targetTime = segmentSeekTime(segment);
  const didSeek = await videoMonitorRef.value?.seekAndPause(targetTime);
  if (!didSeek) return;
  currentTime.value = targetTime;
  activeSegmentId.value = segment.id;
  highlightedTrackId.value = firstTrackForSegment(segment)?.track_id ?? null;
  updateFaceOverlay();
  statusMessage.value = `已定位到 ${formatTime(targetTime)}`;
}

/** 按时间轴输入定位视频时间。 */
async function seekTimelineTime(seconds: number) {
  if (!selectedVideo.value) return;
  const nextTime = clamp(seconds, 0, selectedVideo.value.duration_seconds);
  await videoMonitorRef.value?.seekAndPause(nextTime);
  currentTime.value = nextTime;
  const currentSegment =
    visibleSegments.value.find((segment) => nextTime >= segment.start && nextTime <= segment.end) ??
    null;
  activeSegmentId.value = currentSegment?.id ?? null;
  highlightedTrackId.value = currentSegment
    ? firstTrackForSegment(currentSegment)?.track_id ?? null
    : null;
  updateFaceOverlay();
}

/** 从片段起点附近开始播放当前片段。 */
async function playSegment(segment: SegmentItem) {
  const targetTime = segmentSeekTime(segment);
  activeSegmentId.value = segment.id;
  highlightedTrackId.value = firstTrackForSegment(segment)?.track_id ?? null;
  currentTime.value = targetTime;
  await videoMonitorRef.value?.seekAndPlay(targetTime);
}

/** 计算播放片段时使用的提前定位时间。 */
function segmentSeekTime(segment: SegmentItem) {
  return clamp(segment.start - segmentSeekLeadSeconds, 0, selectedVideo.value?.duration_seconds ?? segment.start);
}

/** 从时间轴快捷键切换视频播放状态。 */
function togglePlaybackFromTimeline() {
  void videoMonitorRef.value?.togglePlayback();
}

/** 同步视频播放时间并更新当前片段和高亮轨迹。 */
function syncCurrentTime(nextTime: number) {
  currentTime.value = nextTime;
  const currentSegment =
    visibleSegments.value.find((segment) => nextTime >= segment.start && nextTime <= segment.end) ??
    null;
  activeSegmentId.value = currentSegment?.id ?? activeSegmentId.value;
  if (currentSegment) {
    highlightedTrackId.value = firstTrackForSegment(currentSegment)?.track_id ?? highlightedTrackId.value;
  }
  updateFaceOverlay();
}

/** 获取视频内人物的展示名称。 */
function personName(personId: number) {
  return people.value.find((person) => person.person_id === personId)?.label ?? `Person ${personId}`;
}

/** 判断视频内人物是否被隐藏。 */
function isHiddenPerson(person: { hidden?: number | boolean | null }) {
  return person.hidden === true || Number(person.hidden ?? 0) === 1;
}

/** 为轨迹选择最合适的代表脸路径。 */
function representativeFaceForTrack(track: TrackItem) {
  return (
    detail.value?.face_crops.find((crop) => crop.track_id === track.track_id)?.path ??
    people.value.find((person) => person.person_id === track.person_id)?.representative_face_path ??
    null
  );
}

/** 定位到轨迹起点并更新高亮片段。 */
function jumpToTrack(track: TrackItem) {
  void videoMonitorRef.value?.seekAndPause(track.start);
  currentTime.value = track.start;
  activeSegmentId.value =
    segments.value.find((segment) => segmentContainsTrack(segment, track.track_id))?.id ?? null;
  updateFaceOverlay();
}

/** 获取片段中第一条可找到的轨迹。 */
function firstTrackForSegment(segment: SegmentItem | null) {
  if (!segment) return null;
  const trackIds = parseTrackIds(segment.track_ids);
  return (
    trackIds
      .map((trackId) => tracks.value.find((track) => track.track_id === trackId))
      .find((track): track is TrackItem => Boolean(track)) ?? null
  );
}

/** 判断片段是否包含指定轨迹。 */
function segmentContainsTrack(segment: SegmentItem, trackId: number) {
  return parseTrackIds(segment.track_ids).includes(trackId);
}

/** 重新测量视频内容区域以刷新人脸框位置。 */
function updateFaceOverlay() {
  window.requestAnimationFrame(() => {
    videoContentRect.value = videoMonitorRef.value?.measureContentRect() ?? null;
  });
}

</script>

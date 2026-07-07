import { computed, ref } from "vue";

/** 主工作区可调整高度的面板 ID。 */
export type ResizablePanelId = "video" | "timeline" | "review";
/** 右侧详情栏可调整高度的面板 ID。 */
export type RightResizablePanelId = "metadata" | "people" | "actions" | "profile" | "segments";

/** 主工作区各面板高度映射。 */
type PanelHeights = Record<ResizablePanelId, number>;
/** 右侧详情栏各面板高度映射。 */
type RightPanelHeights = Partial<Record<RightResizablePanelId, number>>;
/** 主工作区面板拖拽调整状态。 */
type PanelResizeState = {
  panelId: ResizablePanelId;
  startY: number;
  startHeight: number;
};
/** 右侧详情栏面板拖拽调整状态。 */
type RightPanelResizeState = {
  panelId: RightResizablePanelId;
  startY: number;
  startHeight: number;
};

/** 主工作区面板高度的 localStorage key。 */
const panelHeightStorageKey = "facetimemarker.workspace.panelHeights.v8";
/** 右侧详情栏高度的 localStorage key。 */
const rightPanelHeightStorageKey = "facetimemarker.workspace.rightPanelHeights.v2";

/** 主工作区面板默认高度。 */
const defaultPanelHeights: PanelHeights = {
  video: 560,
  timeline: 300,
  review: 2800,
};
/** 主工作区面板高度边界。 */
const panelHeightLimits: Record<ResizablePanelId, { min: number; max: number }> = {
  video: { min: 280, max: 1200 },
  timeline: { min: 180, max: 960 },
  review: { min: 560, max: 4200 },
};
/** 右侧详情栏默认固定高度。 */
const defaultRightPanelHeights: RightPanelHeights = {
  people: 520,
};
/** 右侧详情栏面板高度边界。 */
const rightPanelHeightLimits: Record<RightResizablePanelId, { min: number; max: number }> = {
  metadata: { min: 220, max: 720 },
  people: { min: 240, max: 960 },
  actions: { min: 180, max: 520 },
  profile: { min: 240, max: 760 },
  segments: { min: 220, max: 960 },
};
/** 右侧详情栏可持久化高度的面板顺序。 */
const rightPanelIds: RightResizablePanelId[] = ["metadata", "people", "actions", "profile", "segments"];

/** 管理工作台主面板和右侧面板的尺寸拖拽状态。 */
export function useWorkspacePanelResize(onPanelChange: () => void) {
  const panelHeights = ref<PanelHeights>(loadPanelHeights());
  const rightPanelHeights = ref<RightPanelHeights>(loadRightPanelHeights());
  const panelResizeState = ref<PanelResizeState | null>(null);
  const rightPanelResizeState = ref<RightPanelResizeState | null>(null);

  /** 将面板高度注入给工作台布局 CSS 变量。 */
  const viewerStackStyle = computed(() => ({
    "--video-panel-height": `${panelHeights.value.video}px`,
    "--timeline-panel-height": `${panelHeights.value.timeline}px`,
    "--review-panel-height": `${panelHeights.value.review}px`,
  }));

  /** 生成右侧固定高度面板的样式。 */
  function rightPanelStyle(panelId: RightResizablePanelId) {
    const height = rightPanelHeights.value[panelId];
    return typeof height === "number" ? { height: `${height}px` } : {};
  }

  /** 生成右侧面板外层的布局类。 */
  function rightPanelSectionClass(panelId: RightResizablePanelId) {
    return isRightPanelFixed(panelId) ? "flex flex-col overflow-hidden" : "";
  }

  /** 生成右侧面板内容区的滚动类。 */
  function rightPanelBodyClass(panelId: RightResizablePanelId) {
    return isRightPanelFixed(panelId) ? "min-h-0 flex-1 overflow-y-auto" : "";
  }

  /** 收起上方面板并突出审阅面板高度。 */
  function focusReviewPanelHeight() {
    panelHeights.value = {
      ...panelHeights.value,
      video: clampPanelHeight("video", Math.min(panelHeights.value.video, 360)),
      timeline: clampPanelHeight("timeline", Math.min(panelHeights.value.timeline, 220)),
      review: clampPanelHeight("review", Math.max(panelHeights.value.review, 2800)),
    };
    persistPanelHeights();
    onPanelChange();
  }

  /** 开始拖拽主工作区面板高度。 */
  function startPanelResize(panelId: ResizablePanelId, event: PointerEvent) {
    if (event.button !== 0) return;
    event.preventDefault();
    panelResizeState.value = {
      panelId,
      startY: event.clientY,
      startHeight: panelHeights.value[panelId],
    };
    document.body.classList.add("is-panel-resizing");
    window.addEventListener("pointermove", movePanelResize);
    window.addEventListener("pointerup", stopPanelResize);
    window.addEventListener("pointercancel", stopPanelResize);
  }

  /** 停止拖拽主工作区面板高度。 */
  function stopPanelResize() {
    if (!panelResizeState.value) return;
    panelResizeState.value = null;
    document.body.classList.remove("is-panel-resizing");
    window.removeEventListener("pointermove", movePanelResize);
    window.removeEventListener("pointerup", stopPanelResize);
    window.removeEventListener("pointercancel", stopPanelResize);
    persistPanelHeights();
    onPanelChange();
  }

  /** 处理主工作区面板尺寸键盘调整。 */
  function handlePanelResizeKeydown(panelId: ResizablePanelId, event: KeyboardEvent) {
    const step = event.shiftKey ? 48 : 16;
    if (event.key === "ArrowUp") {
      event.preventDefault();
      resizePanelBy(panelId, -step);
    } else if (event.key === "ArrowDown") {
      event.preventDefault();
      resizePanelBy(panelId, step);
    } else if (event.key === "Home") {
      event.preventDefault();
      resizePanelTo(panelId, panelHeightLimits[panelId].min);
    } else if (event.key === "End") {
      event.preventDefault();
      resizePanelTo(panelId, panelHeightLimits[panelId].max);
    }
  }

  /** 开始拖拽右侧详情栏面板高度。 */
  function startRightPanelResize(panelId: RightResizablePanelId, event: PointerEvent) {
    if (event.button !== 0) return;
    event.preventDefault();
    rightPanelResizeState.value = {
      panelId,
      startY: event.clientY,
      startHeight: currentRightPanelHeight(panelId, event.currentTarget),
    };
    document.body.classList.add("is-panel-resizing");
    window.addEventListener("pointermove", moveRightPanelResize);
    window.addEventListener("pointerup", stopRightPanelResize);
    window.addEventListener("pointercancel", stopRightPanelResize);
  }

  /** 停止拖拽右侧详情栏面板高度。 */
  function stopRightPanelResize() {
    if (!rightPanelResizeState.value) return;
    rightPanelResizeState.value = null;
    document.body.classList.remove("is-panel-resizing");
    window.removeEventListener("pointermove", moveRightPanelResize);
    window.removeEventListener("pointerup", stopRightPanelResize);
    window.removeEventListener("pointercancel", stopRightPanelResize);
    persistRightPanelHeights();
  }

  /** 处理右侧详情栏面板尺寸键盘调整。 */
  function handleRightPanelResizeKeydown(panelId: RightResizablePanelId, event: KeyboardEvent) {
    const step = event.shiftKey ? 48 : 16;
    if (event.key === "ArrowUp") {
      event.preventDefault();
      resizeRightPanelBy(panelId, -step);
    } else if (event.key === "ArrowDown") {
      event.preventDefault();
      resizeRightPanelBy(panelId, step);
    } else if (event.key === "Home") {
      event.preventDefault();
      resizeRightPanelTo(panelId, rightPanelHeightLimits[panelId].min);
    } else if (event.key === "End") {
      event.preventDefault();
      resizeRightPanelTo(panelId, rightPanelHeightLimits[panelId].max);
    }
  }

  /** 指针移动时更新主工作区面板高度。 */
  function movePanelResize(event: PointerEvent) {
    const state = panelResizeState.value;
    if (!state) return;
    const nextHeight = clampPanelHeight(
      state.panelId,
      state.startHeight + event.clientY - state.startY,
    );
    panelHeights.value = {
      ...panelHeights.value,
      [state.panelId]: nextHeight,
    };
    onPanelChange();
  }

  /** 按增量调整主工作区面板高度。 */
  function resizePanelBy(panelId: ResizablePanelId, delta: number) {
    resizePanelTo(panelId, panelHeights.value[panelId] + delta);
  }

  /** 将主工作区面板高度设置到指定值。 */
  function resizePanelTo(panelId: ResizablePanelId, value: number) {
    panelHeights.value = {
      ...panelHeights.value,
      [panelId]: clampPanelHeight(panelId, value),
    };
    persistPanelHeights();
    onPanelChange();
  }

  /** 指针移动时更新右侧详情栏面板高度。 */
  function moveRightPanelResize(event: PointerEvent) {
    const state = rightPanelResizeState.value;
    if (!state) return;
    rightPanelHeights.value = {
      ...rightPanelHeights.value,
      [state.panelId]: clampRightPanelHeight(
        state.panelId,
        state.startHeight + event.clientY - state.startY,
      ),
    };
  }

  /** 按增量调整右侧详情栏面板高度。 */
  function resizeRightPanelBy(panelId: RightResizablePanelId, delta: number) {
    resizeRightPanelTo(panelId, currentRightPanelHeight(panelId) + delta);
  }

  /** 将右侧详情栏面板高度设置到指定值。 */
  function resizeRightPanelTo(panelId: RightResizablePanelId, value: number) {
    rightPanelHeights.value = {
      ...rightPanelHeights.value,
      [panelId]: clampRightPanelHeight(panelId, value),
    };
    persistRightPanelHeights();
  }

  /** 判断右侧详情栏面板是否已有固定高度。 */
  function isRightPanelFixed(panelId: RightResizablePanelId) {
    return typeof rightPanelHeights.value[panelId] === "number";
  }

  /** 获取右侧详情栏面板当前高度。 */
  function currentRightPanelHeight(panelId: RightResizablePanelId, handleTarget: EventTarget | null = null) {
    const stored = rightPanelHeights.value[panelId];
    if (typeof stored === "number") return stored;
    const panel =
      handleTarget instanceof HTMLElement && handleTarget.previousElementSibling instanceof HTMLElement
        ? handleTarget.previousElementSibling
        : null;
    const measured = panel?.getBoundingClientRect().height;
    if (typeof measured === "number" && Number.isFinite(measured) && measured > 0) {
      return measured;
    }
    return defaultRightPanelHeights[panelId] ?? rightPanelHeightLimits[panelId].min;
  }

  /** 从本地存储读取主工作区面板高度。 */
  function loadPanelHeights(): PanelHeights {
    try {
      const raw = window.localStorage.getItem(panelHeightStorageKey);
      if (!raw) return { ...defaultPanelHeights };
      const parsed = JSON.parse(raw) as Partial<PanelHeights>;
      return {
        video: clampPanelHeight("video", parsed.video),
        timeline: clampPanelHeight("timeline", parsed.timeline),
        review: clampPanelHeight("review", parsed.review),
      };
    } catch {
      return { ...defaultPanelHeights };
    }
  }

  /** 持久化主工作区面板高度。 */
  function persistPanelHeights() {
    try {
      window.localStorage.setItem(panelHeightStorageKey, JSON.stringify(panelHeights.value));
    } catch {
      return;
    }
  }

  /** 从本地存储读取右侧详情栏面板高度。 */
  function loadRightPanelHeights(): RightPanelHeights {
    try {
      const raw = window.localStorage.getItem(rightPanelHeightStorageKey);
      if (!raw) return { ...defaultRightPanelHeights };
      const parsed = JSON.parse(raw) as Partial<RightPanelHeights>;
      const next: RightPanelHeights = {};
      for (const panelId of rightPanelIds) {
        if (typeof parsed[panelId] === "number" && Number.isFinite(parsed[panelId])) {
          next[panelId] = clampRightPanelHeight(panelId, parsed[panelId]);
        }
      }
      return {
        ...defaultRightPanelHeights,
        ...next,
      };
    } catch {
      return { ...defaultRightPanelHeights };
    }
  }

  /** 持久化右侧详情栏面板高度。 */
  function persistRightPanelHeights() {
    try {
      window.localStorage.setItem(rightPanelHeightStorageKey, JSON.stringify(rightPanelHeights.value));
    } catch {
      return;
    }
  }

  /** 将主工作区面板高度限制在边界内。 */
  function clampPanelHeight(panelId: ResizablePanelId, value: unknown) {
    const fallback = defaultPanelHeights[panelId];
    const nextValue = typeof value === "number" && Number.isFinite(value) ? value : fallback;
    const limits = panelHeightLimits[panelId];
    return Math.round(clamp(nextValue, limits.min, limits.max));
  }

  /** 将右侧详情栏面板高度限制在边界内。 */
  function clampRightPanelHeight(panelId: RightResizablePanelId, value: unknown) {
    const fallback = defaultRightPanelHeights[panelId] ?? rightPanelHeightLimits[panelId].min;
    const nextValue = typeof value === "number" && Number.isFinite(value) ? value : fallback;
    const limits = rightPanelHeightLimits[panelId];
    return Math.round(clamp(nextValue, limits.min, limits.max));
  }

  return {
    panelHeights,
    rightPanelHeights,
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
  };
}

/** 将数值限制在指定范围内。 */
function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

import { computed, ref, type Ref } from "vue";

import {
  cancelAnalyzeJob,
  getAnalyzeJob,
  getHardware,
  listAnalyzeJobs,
  startAnalyzeBatchJob,
  startAnalyzeJob,
  uploadVideo,
  type AnalyzeJobStatus,
  type HardwareProfileId,
  type HardwareSummary,
  type VideoDetail,
} from "../api";
import {
  clamp,
  formatCount,
  formatDuration,
  isSupportedVideo,
  parseServerVideoPaths,
  sleep,
  videoDisplayTitle,
} from "../components/workspace/workspaceUtils";

export type PresetId = "fast" | "balanced" | "crowd";

type ImportQueueItem = {
  id: string;
  file: File;
};

type UseWorkspaceAnalysisOptions = {
  detail: Ref<VideoDetail | null>;
  statusMessage: Ref<string>;
  errorMessage: Ref<string>;
  isImporting: Ref<boolean>;
  refreshAll: () => Promise<void>;
  selectVideo: (id: number) => Promise<void>;
};

/** 管理上传队列、后台分析任务、硬件选项和进度展示。 */
export function useWorkspaceAnalysis(options: UseWorkspaceAnalysisOptions) {
  const timelinePath = ref("_outputs/palace/timeline.json");
  const serverVideoPath = ref("");
  const selectedPreset = ref<PresetId>("fast");
  const analysisSeriesName = ref("");
  const analysisConfigPath = ref("");
  const analysisUseCache = ref(true);
  const expectedPeopleCount = ref<number | null>(null);
  const hardwareSummary = ref<HardwareSummary | null>(null);
  const hardwareProfile = ref<HardwareProfileId>("auto");
  const allowCpuFallback = ref(true);
  const isUploading = ref(false);
  const isUploadQueueProcessing = ref(false);
  const isAnalyzing = ref(false);
  const analysisJob = ref<AnalyzeJobStatus | null>(null);
  const analysisJobs = ref<AnalyzeJobStatus[]>([]);
  const analysisStartedAt = ref<number | null>(null);
  const elapsedNow = ref(Date.now());
  const importQueue = ref<ImportQueueItem[]>([]);

  const pendingImportCount = computed(() => importQueue.value.length);
  const canCancelAnalysis = computed(() => {
    return (
      isAnalyzing.value &&
      analysisJob.value !== null &&
      (analysisJob.value.status === "queued" || analysisJob.value.status === "running")
    );
  });
  const busyLabel = computed(() => {
    if (isUploading.value) return "上传中";
    if (isAnalyzing.value) return "分析中";
    if (options.isImporting.value) return "导入中";
    return "处理中";
  });
  const operationProgress = computed(() => {
    if (isAnalyzing.value && analysisJob.value) return clamp(analysisJob.value.progress, 0, 1);
    if (isUploading.value) return 0.12;
    if (options.isImporting.value) return 0.45;
    return 0;
  });
  const operationProgressPercent = computed(() => Math.round(operationProgress.value * 100));
  const operationProgressMessage = computed(() => {
    if (isAnalyzing.value && analysisJob.value && analysisJob.value.total > 1) {
      return `${analysisJob.value.message} (${analysisJob.value.completed}/${analysisJob.value.total})`;
    }
    if (isAnalyzing.value && analysisJob.value?.message) return analysisJob.value.message;
    if (options.statusMessage.value) return options.statusMessage.value;
    return busyLabel.value;
  });
  const analysisElapsedLabel = computed(() => {
    if (!analysisStartedAt.value) return "0:00";
    return formatDuration((elapsedNow.value - analysisStartedAt.value) / 1000);
  });

  async function refreshHardware() {
    try {
      hardwareSummary.value = await getHardware();
    } catch {
      hardwareSummary.value = null;
    }
  }

  async function refreshAnalysisJobs() {
    try {
      analysisJobs.value = await listAnalyzeJobs(10);
    } catch {
      analysisJobs.value = [];
    }
  }

  function setCurrentAnalysisJob(job: AnalyzeJobStatus) {
    analysisJob.value = job;
    const rest = analysisJobs.value.filter((item) => item.job_id !== job.job_id);
    analysisJobs.value = [job, ...rest].slice(0, 10);
  }

  function isActiveAnalyzeJob(job: AnalyzeJobStatus) {
    return job.status === "queued" || job.status === "running";
  }

  async function restoreLatestActiveAnalysisJob() {
    const activeJob = analysisJobs.value.find(isActiveAnalyzeJob);
    if (!activeJob || isAnalyzing.value) return;
    isAnalyzing.value = true;
    analysisStartedAt.value = Date.now();
    elapsedNow.value = Date.now();
    setCurrentAnalysisJob(activeJob);
    options.statusMessage.value = "已恢复后台分析任务";
    try {
      let job = activeJob;
      while (isActiveAnalyzeJob(job)) {
        await sleep(900);
        job = await getAnalyzeJob(job.job_id);
        setCurrentAnalysisJob(job);
      }
      await handleAnalyzeJobFinished(job);
    } catch {
      options.errorMessage.value = "恢复分析任务失败，请检查后端日志。";
    } finally {
      isAnalyzing.value = false;
      analysisStartedAt.value = null;
      await refreshAnalysisJobs();
    }
  }

  function processVideoFiles(files: File[]) {
    const supportedFiles = files.filter((file) => isSupportedVideo(file.name));
    const rejectedCount = files.length - supportedFiles.length;
    if (rejectedCount > 0) {
      options.errorMessage.value = `已跳过 ${formatCount(rejectedCount)} 个不支持的文件。`;
    } else {
      options.errorMessage.value = "";
    }
    if (supportedFiles.length === 0) return;

    importQueue.value = [
      ...importQueue.value,
      ...supportedFiles.map((file) => ({
        id: `${file.name}-${file.size}-${file.lastModified}-${Math.random().toString(36).slice(2)}`,
        file,
      })),
    ];
    options.statusMessage.value = `已加入导入队列 ${formatCount(supportedFiles.length)} 个文件`;
    void drainImportQueue();
  }

  async function analyzeServerPath() {
    const videoPaths = parseServerVideoPaths(serverVideoPath.value);
    if (videoPaths.length === 0) return;

    options.errorMessage.value = "";
    try {
      await runAnalyzeJob(videoPaths);
    } catch {
      options.errorMessage.value = "分析失败，请确认视频路径存在且后端依赖已安装。";
    }
  }

  async function reanalyzeSelectedVideo() {
    if (!options.detail.value) return;
    const video = options.detail.value;
    options.errorMessage.value = "";
    try {
      await runAnalyzeJob(
        video.path,
        false,
        videoDisplayTitle(video),
        video.series_name,
        video.original_filename,
        video.source_path || video.path,
        video.source_directory,
      );
    } catch {
      options.errorMessage.value = "重新识别失败，请检查后端日志。";
    }
  }

  async function cancelCurrentAnalysis() {
    const jobId = analysisJob.value?.job_id;
    if (!jobId || !canCancelAnalysis.value) return;
    try {
      setCurrentAnalysisJob(await cancelAnalyzeJob(jobId));
      await refreshAnalysisJobs();
      options.statusMessage.value = "分析已终止";
    } catch {
      options.errorMessage.value = "终止分析失败，请稍后刷新任务状态。";
    }
  }

  async function drainImportQueue() {
    if (isUploadQueueProcessing.value || importQueue.value.length === 0) return;
    isUploadQueueProcessing.value = true;
    try {
      while (importQueue.value.length > 0) {
        const batch = importQueue.value;
        importQueue.value = [];
        await uploadAndAnalyzeBatch(batch);
      }
    } finally {
      isUploadQueueProcessing.value = false;
    }
  }

  async function uploadAndAnalyzeBatch(batch: ImportQueueItem[]) {
    if (batch.length === 0) return;
    options.errorMessage.value = "";
    const uploadedItems: Awaited<ReturnType<typeof uploadVideo>>[] = [];
    try {
      isUploading.value = true;
      for (const [index, item] of batch.entries()) {
        options.statusMessage.value = `正在上传 ${index + 1}/${batch.length}：${item.file.name}`;
        uploadedItems.push(await uploadVideo(item.file));
      }
      isUploading.value = false;
      const videoPaths = uploadedItems.map((item) => item.video_path);
      if (uploadedItems.length === 1) {
        const uploaded = uploadedItems[0];
        await runAnalyzeJob(
          uploaded.video_path,
          analysisUseCache.value,
          uploaded.filename,
          analysisSeriesName.value,
          uploaded.filename,
          uploaded.source_path,
          uploaded.source_directory,
        );
      } else {
        await runAnalyzeJob(videoPaths, analysisUseCache.value, null, analysisSeriesName.value);
      }
    } catch {
      options.errorMessage.value = "上传或分析失败，请检查后端日志。";
    } finally {
      isUploading.value = false;
    }
  }

  async function runAnalyzeJob(
    videoPathOrPaths: string | string[],
    useCache = analysisUseCache.value,
    displayTitle: string | null = null,
    seriesName = analysisSeriesName.value,
    originalFilename: string | null = null,
    sourcePath: string | null = null,
    sourceDirectory: string | null = null,
  ) {
    isAnalyzing.value = true;
    analysisStartedAt.value = Date.now();
    elapsedNow.value = Date.now();
    analysisJob.value = null;
    const videoPaths = Array.isArray(videoPathOrPaths) ? videoPathOrPaths : [videoPathOrPaths];
    const peopleCountLabel =
      expectedPeopleCount.value === null ? "Auto" : `${expectedPeopleCount.value} 人`;
    const nextSeriesName = seriesName.trim() || null;
    const configPath = analysisConfigPath.value.trim() || null;
    options.statusMessage.value =
      videoPaths.length > 1
        ? `批量分析 ${videoPaths.length} 个视频 / ${peopleCountLabel}`
        : `${useCache ? "视频分析中" : "重新识别中"} / ${peopleCountLabel}`;
    try {
      let job =
        videoPaths.length > 1
          ? await startAnalyzeBatchJob(
              videoPaths,
              selectedPreset.value,
              useCache,
              expectedPeopleCount.value,
              nextSeriesName,
              hardwareProfile.value,
              allowCpuFallback.value,
              configPath,
            )
          : await startAnalyzeJob(
              videoPaths[0],
              selectedPreset.value,
              useCache,
              expectedPeopleCount.value,
              displayTitle,
              nextSeriesName,
              originalFilename,
              sourcePath,
              sourceDirectory,
              hardwareProfile.value,
              allowCpuFallback.value,
              configPath,
            );
      setCurrentAnalysisJob(job);
      while (job.status === "queued" || job.status === "running") {
        await sleep(900);
        job = await getAnalyzeJob(job.job_id);
        setCurrentAnalysisJob(job);
      }
      await handleAnalyzeJobFinished(job);
    } finally {
      isAnalyzing.value = false;
      analysisStartedAt.value = null;
      await refreshAnalysisJobs();
    }
  }

  async function handleAnalyzeJobFinished(job: AnalyzeJobStatus) {
    if (job.status === "canceled") {
      options.statusMessage.value = "分析已终止";
      return;
    }
    if (job.status === "failed") {
      throw new Error(job.error ?? "分析失败");
    }
    if (job.video_id === null || job.timeline_path === null) {
      throw new Error("分析任务未返回结果");
    }
    timelinePath.value = job.timeline_path;
    await options.refreshAll();
    const lastSucceededItem = [...job.items].reverse().find((item) => item.video_id !== null);
    const nextVideoId = lastSucceededItem?.video_id ?? job.video_id;
    if (nextVideoId === null) {
      throw new Error("分析任务未返回可打开的视频");
    }
    await options.selectVideo(nextVideoId);
    options.statusMessage.value =
      job.total > 1
        ? `批量分析完成：成功 ${job.completed} 个，失败 ${job.failed} 个`
        : "视频分析完成";
  }

  return {
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
  };
}

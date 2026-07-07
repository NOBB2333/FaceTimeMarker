<template>
  <section class="profiles-page grid min-h-0 overflow-hidden bg-[#090b0f] text-[#eef2f7]">
    <ProfilesSidebar
      :browse-mode="browseMode"
      v-model:query="query"
      v-model:manual-profile-label="manualProfileLabel"
      :search-placeholder="searchPlaceholder"
      :filtered-profiles="filteredProfiles"
      :filtered-videos="filteredVideos"
      :filtered-deleted-profiles="filteredDeletedProfiles"
      :selected-profile-id="selectedProfileId"
      :selected-video-id="selectedVideoId"
      :selected-local-person-target="selectedLocalPersonTarget"
      :selected-reference-count="selectedReferenceCandidates.length"
      :can-submit-manual-profile="canSubmitManualProfile"
      :is-loading="isLoading"
      :is-restoring-profile="isRestoringProfile"
      :is-purging-profile="isPurgingProfile"
      @update:browse-mode="setBrowseMode"
      @refresh="loadAll"
      @submit-manual-profile="submitManualProfile"
      @select-profile="selectProfile"
      @select-work="selectWork"
      @restore-profile="submitRestoreDeletedProfile"
      @purge-profile="submitPurgeDeletedProfile"
    />

    <section class="profile-scroll-area h-full min-h-0 max-h-full overflow-y-scroll overscroll-contain bg-[#080a0d]">
      <div v-if="errorMessage" class="break-all border-b border-[#ff5a5a]/30 bg-[#2a1214] px-5 py-3 text-sm text-[#ffb4b4]">
        {{ errorMessage }}
      </div>
      <div v-else-if="statusMessage" class="break-all border-b border-[#34d5c8]/20 bg-[#0b2426] px-5 py-3 text-sm text-[#9ff4ec]">
        {{ statusMessage }}
      </div>

      <template v-if="browseMode === 'person'">
        <div v-if="selectedProfile" class="profile-detail">
          <header class="border-b border-white/10 bg-[#0f1319] px-5 py-5">
            <div class="flex min-w-0 flex-wrap gap-4">
              <div class="flex min-w-0 flex-1 gap-4">
                <img
                  v-if="selectedProfile.representative_face_path"
                  class="h-24 w-24 shrink-0 object-cover"
                  :src="mediaUrl(selectedProfile.representative_face_path)"
                  alt=""
                />
                <span
                  v-else
                  class="grid h-24 w-24 shrink-0 place-items-center border border-white/10 bg-[#090d12] text-[#536171]"
                >
                  <UserRound class="h-9 w-9" aria-hidden="true" />
                </span>
                <div class="min-w-0 flex-1">
                  <p class="timecode text-xs font-semibold text-[#34d5c8]">
                    {{ selectedProfile.global_person_id }}
                  </p>
                  <h2 class="mt-2 truncate text-2xl font-semibold text-[#f8fafc]">
                    {{ profileName(selectedProfile) }}
                  </h2>
                  <div class="mt-4 flex flex-wrap gap-2 text-xs text-[#8f9bac]">
                    <span class="border border-white/10 bg-[#111821] px-2.5 py-1">
                      {{ formatCount(selectedProfile.observation_count) }} 次观测
                    </span>
                    <span class="border border-white/10 bg-[#111821] px-2.5 py-1">
                      {{ formatCount(workCount) }} 部作品
                    </span>
                    <span class="border border-white/10 bg-[#111821] px-2.5 py-1">
                      {{ formatDuration(selectedProfile.total_duration) }}
                    </span>
                    <span class="border border-white/10 bg-[#111821] px-2.5 py-1">
                      {{ formatCount(selectedProfile.confirmed_count) }} 已确认
                    </span>
                  </div>
                  <div class="mt-4 max-w-3xl">
                    <FourViewStatus
	                      :set-count="profileFourViewSetCount"
		                      :selected-count="selectedReferenceCandidates.length"
                          :selectable-count="profileReferenceCandidates.length"
		                      :assets="profileFourViewAssets"
	                        :uploading="isUploadingFourViewAsset"
	                        :generating="isGeneratingFourViewAsset"
	                        can-upload
                          can-select-all
                          select-all-label="全选当前人物"
                          selection-label="当前人物参考"
		                      compact
			                      @generate="queueFourViewGeneration"
			                      @preview-asset="openFourViewAsset"
	                        @delete-asset="removeFourViewAsset"
		                        @upload-asset="uploadSelectedProfileFourView"
                          @select-all="selectAllProfileReferences"
                          @clear-selection="resetReferenceSelection"
		                    />
                  </div>
                </div>
              </div>
            </div>
          </header>

	          <div class="grid gap-0 xl:grid-cols-[minmax(0,1fr)_340px]">
		          <main class="min-w-0">
              <section class="border-b border-white/10 px-5 py-4">
                <div class="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h3 class="text-sm font-semibold text-[#f8fafc]">作品形象</h3>
                    <p class="mt-1 text-xs text-[#7d8998]">每部作品下展示这个人物的全部可用截图</p>
                  </div>
                  <div class="flex items-center gap-3">
                    <span class="text-xs text-[#7d8998]">{{ formatCount(groupedWorks.length) }} 组</span>
	                    <ReferenceDisplayModeToggle v-model="workReferenceDisplayMode" />
                  </div>
                </div>
              </section>

              <article
                v-for="work in groupedWorks"
                :key="work.key"
                class="border-b border-white/10 px-5 py-4"
              >
                <div class="flex flex-wrap items-center justify-between gap-3">
                  <div class="min-w-0">
	                    <h4 class="truncate text-sm font-semibold text-[#f8fafc]">{{ work.title }}</h4>
	                    <p class="mt-1 truncate text-xs text-[#7d8998]">{{ work.sourceDirectory || work.seriesName || "未记录来源目录" }}</p>
                  </div>
                  <div class="flex flex-wrap items-center justify-end gap-3">
                    <FourViewAssetStrip
	                      :assets="profileFourViewAssets"
	                      @preview-asset="openFourViewAsset"
                      @delete-asset="removeFourViewAsset"
	                    />
	                    <div class="flex gap-2 text-xs text-[#8f9bac]">
	                      <span>{{ formatCount(work.items.length) }} 形象</span>
	                      <span>{{ formatDuration(work.totalDuration) }}</span>
	                    </div>
	                  </div>
	                </div>
	                <div class="mt-3 flex flex-wrap gap-2">
	                  <button
	                    v-for="item in work.items"
	                    :key="item.id"
	                    class="inline-flex h-8 items-center justify-center gap-2 border border-white/10 bg-[#151b23] px-3 text-xs font-semibold text-[#cbd5e1] transition-colors duration-150 hover:border-[#34d5c8]/60 hover:text-[#34d5c8]"
	                    type="button"
	                    @click="selectAllProfileObservationReferences(item)"
	                  >
	                    <span>全选此人物</span>
	                    <span class="timecode text-[#34d5c8]">{{ item.label }}</span>
	                    <span class="text-[#8f9bac]">{{ formatCount(profileObservationReferenceCandidates(item).length) }} 张</span>
	                    <span v-if="selectedReferenceCount(profileObservationReferenceCandidates(item)) > 0" class="text-[#f5c451]">
	                      {{ formatCount(selectedReferenceCount(profileObservationReferenceCandidates(item))) }} 已选
	                    </span>
	                  </button>
	                </div>

                <ReferenceFrameGrid
                  class="mt-4"
                  :candidates="profileWorkCandidates(work)"
                  :selected-ids="selectedReferenceIds"
                  :display-mode="workReferenceDisplayMode"
                  @toggle="toggleReferenceCandidate"
                  @preview="previewReferenceCandidate"
                />
              </article>
            </main>

		            <aside class="profile-preview-rail min-h-0 border-l border-white/10 bg-[#0f1319]">
                  <SegmentPreviewPanel
                    ref="segmentPreviewPanelRef"
                    :work="segmentPreviewWork"
                    :meta="segmentPreviewMeta"
                    :title="segmentPreviewTitle"
                    :loading="segmentPreviewLoading"
                    :error="segmentPreviewError"
                    :can-step="canStepSegmentPreview"
                    :can-play="Boolean(activeSegmentPreview)"
                    @step="stepSegmentPreview"
                    @play="syncSegmentPreviewVideo(true)"
                    @loaded-metadata="syncSegmentPreviewVideo(false)"
                  />
                  <ReferenceCandidateRail
                    :candidates="referenceRailCandidates"
                    :selected-count="selectedReferenceCandidates.length"
                    @open="openReferenceCandidate"
                  />

                <ProfileManagementPanel
                  v-model:profile-label="profileLabelDraft"
                  v-model:merge-source-id="mergeSourceGlobalPersonId"
                  :selected-profile="selectedProfile"
                  :merge-source-profiles="mergeSourceProfiles"
                  :profile-actions="profileActions"
                  :reference-count="referenceCount"
                  :can-rename="canRenameProfile"
                  :can-merge="canMergeProfile"
                  :is-renaming="isRenamingProfile"
                  :is-merging="isMergingProfile"
                  :is-deleting="isDeletingProfile"
                  @rename="submitRenameSelectedProfile"
                  @merge="submitMergeSelectedProfile"
                  @delete="submitDeleteSelectedProfile"
                />
	            </aside>
          </div>
        </div>

        <EmptyState v-else :label="isLoading ? '正在读取人物档案' : '没有可用人物档案'" />
      </template>

      <template v-else-if="browseMode === 'work'">
        <div v-if="selectedWork" class="profile-detail">
          <header class="border-b border-white/10 bg-[#0f1319] px-5 py-5">
            <div class="flex flex-wrap items-start justify-between gap-5">
              <div class="min-w-0">
	                <p class="text-xs font-semibold text-[#34d5c8]">{{ selectedWork.series_name || "未分组" }}</p>
	                <h2 class="mt-2 truncate text-2xl font-semibold text-[#f8fafc]">{{ videoDisplayTitle(selectedWork) }}</h2>
	                <p class="mt-2 max-w-3xl truncate text-xs text-[#7d8998]">
	                  {{ selectedWork.source_path || selectedWork.path }}
	                </p>
	                <p class="mt-1 max-w-3xl truncate text-xs text-[#7d8998]">
	                  {{ selectedWork.source_directory || "未记录来源目录" }}
	                </p>
                <div class="mt-4 flex flex-wrap gap-2 text-xs text-[#8f9bac]">
	                  <span class="border border-white/10 bg-[#111821] px-2.5 py-1">
		                    {{ formatCount(workPeople.length) }} 可见人物
	                  </span>
                  <span class="border border-[#f5c451]/25 bg-[#2a2414] px-2.5 py-1 text-[#f5c451]">
                    {{ formatCount(workFourViewCompletedPersonCount) }} / {{ formatCount(workVisiblePersonCount) }} 已有四视图
                  </span>
	                  <span class="border border-white/10 bg-[#111821] px-2.5 py-1">
	                    {{ formatCount(selectedWork.segments.length) }} 片段
	                  </span>
                  <span class="border border-white/10 bg-[#111821] px-2.5 py-1">
                    {{ formatCount(selectedWork.tracks.length) }} 轨迹
                  </span>
	                  <span class="border border-white/10 bg-[#111821] px-2.5 py-1">
	                    {{ formatDuration(selectedWork.duration_seconds) }}
	                  </span>
	                </div>
                <div class="mt-4 max-w-3xl">
                  <FourViewStatus
                    :set-count="workFourViewSetCount"
                    :selected-count="selectedReferenceCandidates.length"
                    :selectable-count="workReferenceCandidateCount"
                    :assets="workFocusedFourViewAssets"
                    :generating="isGeneratingFourViewAsset"
                    compact
                    selection-label="作品参考"
                    @generate="queueFourViewGeneration"
                    @preview-asset="openFourViewAsset"
                    @delete-asset="removeFourViewAsset"
                    @clear-selection="resetReferenceSelection"
                  />
                </div>
	              </div>
	              <div class="grid w-full max-w-[420px] grid-cols-2 gap-2 text-xs text-[#8f9bac]">
	                <MetricBox label="分辨率" :value="`${selectedWork.width} x ${selectedWork.height}`" />
	                <MetricBox label="帧率" :value="`${formatDecimal(selectedWork.fps)} FPS`" />
                <MetricBox label="候选帧" :value="`${formatCount(workReferenceCandidateCount)} 张`" />
                <MetricBox label="四视图" :value="`${formatCount(workFourViewCompletedPersonCount)} / ${formatCount(workVisiblePersonCount)} 人物`" />
	              </div>
	            </div>
	          </header>

	          <div class="grid gap-0 xl:grid-cols-[minmax(0,1fr)_340px]">
	          <main class="min-w-0">
	            <section class="border-b border-white/10 px-5 py-4">
		            <div class="flex flex-wrap items-center justify-between gap-3">
		              <div>
		                <h3 class="text-sm font-semibold text-[#f8fafc]">本作品人物</h3>
		                <p class="mt-1 text-xs text-[#7d8998]">按单个视频结果展示，每个人下方列出可选参考帧</p>
		              </div>
			              <ReferenceDisplayModeToggle v-model="workReferenceDisplayMode" />
	              </div>
            </section>

            <div class="space-y-4 px-5 py-5">
	              <section
	                v-for="person in workPeople"
	                :key="person.person_id"
	                class="border border-white/10 bg-[#0d1117]"
	                :class="isHiddenPerson(person) ? 'opacity-60' : ''"
	              >
	                <div class="flex flex-wrap items-start gap-4 border-b border-white/10 px-4 py-3">
	                  <div class="h-20 w-20 shrink-0 overflow-hidden border border-white/10 bg-[#090d12]">
	                    <img
	                      v-if="person.representative_face_path"
	                      class="h-full w-full object-cover"
	                      :src="mediaUrl(person.representative_face_path)"
	                      alt=""
	                    />
	                    <span v-else class="grid h-full w-full place-items-center text-[#536171]">
	                      <Images class="h-7 w-7" aria-hidden="true" />
	                    </span>
	                  </div>
	                  <div class="min-w-[220px] flex-1">
	                    <div class="flex flex-wrap items-center gap-2">
	                      <h4 class="text-sm font-semibold text-[#f8fafc]">
	                        {{ person.label }}{{ isHiddenPerson(person) ? " / 已隐藏" : "" }}
	                      </h4>
	                      <span v-if="person.global_person_id" class="timecode text-xs text-[#34d5c8]">
	                        {{ person.global_person_id }}
	                      </span>
	                    </div>
	                    <div class="mt-2 flex flex-wrap gap-2 text-[11px] text-[#8f9bac]">
	                      <span>{{ formatCount(person.appearances) }} 片段</span>
	                      <span>{{ formatCount(person.detection_count) }} 框</span>
		                      <span>{{ formatDuration(person.total_duration) }}</span>
		                      <span>{{ formatCount(workPersonReferenceCandidates(person).length) }} 候选帧</span>
                          <span>{{ selectedReferenceCount(workPersonReferenceCandidates(person)) }} 已选</span>
		                    </div>
		                  </div>
		                  <FourViewAssetStrip
			                    :assets="fourViewAssetsForWorkPerson(person)"
		                    @preview-asset="openFourViewAsset"
                      @delete-asset="removeFourViewAsset"
		                  />
	                  <button
	                    class="grid h-8 w-8 shrink-0 place-items-center border border-white/10 bg-[#151b23] text-[#8f9bac] transition-colors duration-150 hover:border-[#34d5c8]/60 hover:text-[#34d5c8] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]"
	                    type="button"
	                    :aria-label="isHiddenPerson(person) ? '恢复显示人物' : '隐藏人物'"
	                    @click.stop="toggleWorkPersonHidden(person)"
		                    >
		                    <Eye v-if="isHiddenPerson(person)" class="h-4 w-4" aria-hidden="true" />
		                    <EyeOff v-else class="h-4 w-4" aria-hidden="true" />
		                  </button>
                      <button
                        class="inline-flex h-8 shrink-0 items-center justify-center border border-white/10 bg-[#151b23] px-3 text-xs font-semibold text-[#cbd5e1] transition-colors duration-150 hover:border-[#34d5c8]/60 hover:text-[#34d5c8] disabled:opacity-40"
                        type="button"
                        :disabled="workPersonReferenceCandidates(person).length === 0"
                        @click="selectAllWorkPersonReferences(person)"
                      >
                        全选此人物
                      </button>
		                </div>
	                <div class="px-4 py-3">
	                  <div
	                    v-if="workPersonReferenceCandidates(person).length === 0"
	                    class="border border-dashed border-white/10 bg-[#090d12] px-3 py-8 text-center text-xs text-[#697586]"
	                  >
	                    这个人物暂时没有可用截图
	                  </div>
	                  <ReferenceFrameGrid
	                    v-else
	                    :candidates="workPersonReferenceCandidates(person)"
	                    :selected-ids="selectedReferenceIds"
	                    :display-mode="workReferenceDisplayMode"
	                    @toggle="toggleReferenceCandidate"
	                    @preview="previewReferenceCandidate"
	                  />
	                </div>
	              </section>
	            </div>
	          </main>
		          <aside class="profile-preview-rail min-h-0 border-l border-white/10 bg-[#0f1319]">
                <SegmentPreviewPanel
                  ref="segmentPreviewPanelRef"
                  :work="segmentPreviewWork"
                  :meta="segmentPreviewMeta"
                  :title="segmentPreviewTitle"
                  :loading="segmentPreviewLoading"
                  :error="segmentPreviewError"
                  :can-step="canStepSegmentPreview"
                  :can-play="Boolean(activeSegmentPreview)"
                  @step="stepSegmentPreview"
                  @play="syncSegmentPreviewVideo(true)"
                  @loaded-metadata="syncSegmentPreviewVideo(false)"
                />
                <ReferenceCandidateRail
                  :candidates="referenceRailCandidates"
                  :selected-count="selectedReferenceCandidates.length"
                  @open="openReferenceCandidate"
                />
	            <section class="px-4 py-3">
		              <FourViewStatus
		                :set-count="workFourViewSetCount"
		                :selected-count="selectedReferenceCandidates.length"
                    :selectable-count="workReferenceCandidateCount"
	                  :assets="workFocusedFourViewAssets"
	                  :generating="isGeneratingFourViewAsset"
		                dense
			                @generate="queueFourViewGeneration"
		                  @preview-asset="openFourViewAsset"
	                  @delete-asset="removeFourViewAsset"
                    @clear-selection="resetReferenceSelection"
			              />
	            </section>
	          </aside>
	          </div>
	        </div>

        <EmptyState v-else :label="isLoading ? '正在读取作品' : '没有可用作品'" />
      </template>

      <template v-else>
        <EmptyState :label="isLoading ? '正在读取档案回收站' : '从左侧回收站恢复或彻底删除档案'" />
      </template>
    </section>

    <FourViewAssetDialog
      :asset="selectedFourViewAsset"
      :asset-index="selectedFourViewAssetIndex"
      :asset-count="selectedFourViewAssetList.length"
      @close="closeFourViewAsset"
      @previous="showPreviousFourViewAsset"
      @next="showNextFourViewAsset"
    />
    <ReferenceCandidateDialog :candidate="selectedReferenceCandidate" @close="closeReferenceCandidate" />
  </section>
</template>

<script setup lang="ts">
import {
  Eye,
  EyeOff,
  Images,
  UserRound,
} from "@lucide/vue";
import { computed, nextTick, onMounted, ref, watch } from "vue";

import EmptyState from "../components/profiles/EmptyState.vue";
import FourViewAssetDialog from "../components/profiles/FourViewAssetDialog.vue";
import FourViewAssetStrip from "../components/profiles/FourViewAssetStrip.vue";
import FourViewStatus from "../components/profiles/FourViewStatus.vue";
import MetricBox from "../components/profiles/MetricBox.vue";
import ProfileManagementPanel from "../components/profiles/ProfileManagementPanel.vue";
import ProfilesSidebar from "../components/profiles/ProfilesSidebar.vue";
import ReferenceCandidateRail from "../components/profiles/ReferenceCandidateRail.vue";
import ReferenceCandidateDialog from "../components/profiles/ReferenceCandidateDialog.vue";
import ReferenceDisplayModeToggle from "../components/profiles/ReferenceDisplayModeToggle.vue";
import ReferenceFrameGrid, {
  type ReferenceDisplayMode,
  type ReferenceFrameCandidate,
} from "../components/profiles/ReferenceFrameGrid.vue";
import SegmentPreviewPanel from "../components/profiles/SegmentPreviewPanel.vue";
import {
  createGlobalPersonFromLocal,
  createManualGlobalPerson,
  deleteFourViewAsset,
  deleteGlobalPerson,
  generateFourViewAsset,
  getVideo,
  listFourViewAssets,
  listGlobalPersonActions,
  listGlobalObservations,
  listGlobalPeople,
  listVideos,
  mediaUrl,
  mergeGlobalPeople,
  moveFourViewAssets,
  purgeGlobalPerson,
  renameGlobalPerson,
  restoreGlobalPerson,
  setPersonHidden,
  uploadFourViewAsset,
  videoFrameUrl,
  type FaceCropItem,
  type FourViewReferenceInput,
  type FourViewAssetItem,
  type GlobalPersonActionItem,
  type GlobalObservationItem,
  type GlobalPersonItem,
  type PersonItem,
  type SegmentItem,
  type VideoDetail,
  type VideoItem,
} from "../api";

/** 档案页左侧列表的浏览模式。 */
type BrowseMode = "person" | "work" | "trash";
/** 作品人物参考素材的展示方式。 */
type WorkReferenceDisplayMode = ReferenceDisplayMode;
/** 按作品聚合后的全局观测分组。 */
type WorkGroup = {
  key: string;
  title: string;
  seriesName: string;
  sourceDirectory: string;
  totalDuration: number;
  items: GlobalObservationItem[];
};
/** 当前选中的参考素材如果能定位到单个本地人物，就可以直接拆成新档案。 */
type SelectedLocalPersonTarget = {
  videoId: number;
  personId: number;
  label: string;
  workTitle: string;
  previousGlobalPersonId: string | null;
  referenceCount: number;
};
/** 可用于生成四视图参考的候选素材。 */
type ReferenceCandidate = ReferenceFrameCandidate;
type FourViewAsset = FourViewAssetItem;
type SegmentPreviewPanelExposed = {
  getVideoElement: () => HTMLVideoElement | null;
};

const browseMode = ref<BrowseMode>("person");
const profiles = ref<GlobalPersonItem[]>([]);
const deletedProfiles = ref<GlobalPersonItem[]>([]);
const observations = ref<GlobalObservationItem[]>([]);
const videos = ref<VideoItem[]>([]);
const selectedProfileId = ref<string | null>(null);
const selectedVideoId = ref<number | null>(null);
const selectedWork = ref<VideoDetail | null>(null);
const selectedReferenceIds = ref<string[]>([]);
const workReferenceDisplayMode = ref<WorkReferenceDisplayMode>("frame");
const profileVideoDetails = ref<Record<number, VideoDetail>>({});
const profileFourViewAssets = ref<FourViewAsset[]>([]);
const generatedWorkFourViewAssets = ref<FourViewAsset[]>([]);
const workFourViewAssetsByGlobalPersonId = ref<Record<string, FourViewAsset[]>>({});
const segmentPreviewPanelRef = ref<SegmentPreviewPanelExposed | null>(null);
const segmentPreviewWork = ref<VideoDetail | null>(null);
const segmentPreviewPersonId = ref<number | null>(null);
const segmentPreviewIndex = ref(0);
const segmentPreviewTargetTime = ref<number | null>(null);
const segmentPreviewLoading = ref(false);
const segmentPreviewError = ref("");
const selectedFourViewAsset = ref<FourViewAsset | null>(null);
const selectedFourViewAssetList = ref<FourViewAsset[]>([]);
const selectedFourViewAssetIndex = ref(0);
const selectedReferenceCandidate = ref<ReferenceCandidate | null>(null);
const profileActions = ref<GlobalPersonActionItem[]>([]);
const manualProfileLabel = ref("");
const profileLabelDraft = ref("");
const mergeSourceGlobalPersonId = ref("");
const isCreatingProfile = ref(false);
const isUploadingFourViewAsset = ref(false);
const isGeneratingFourViewAsset = ref(false);
const isRenamingProfile = ref(false);
const isDeletingProfile = ref(false);
const isRestoringProfile = ref(false);
const isPurgingProfile = ref(false);
const isMergingProfile = ref(false);
const query = ref("");
const errorMessage = ref("");
const statusMessage = ref("");
const isLoading = ref(false);
const numberFormatter = new Intl.NumberFormat("zh-CN");
const decimalFormatter = new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 1 });
const videoDetailCache = new Map<number, VideoDetail>();
const segmentPreviewLeadSeconds = 1.0;
/** 按搜索词过滤并排序后的人物档案列表。 */
const filteredProfiles = computed(() => {
  const keyword = query.value.trim().toLowerCase();
  const source = [...profiles.value].sort((a, b) => {
    return b.observation_count - a.observation_count || profileName(a).localeCompare(profileName(b));
  });
  if (!keyword || browseMode.value !== "person") return source;
  return source.filter((person) => {
    return (
      profileName(person).toLowerCase().includes(keyword) ||
      person.global_person_id.toLowerCase().includes(keyword)
    );
  });
});

/** 按搜索词过滤后的档案回收站列表。 */
const filteredDeletedProfiles = computed(() => {
  const keyword = query.value.trim().toLowerCase();
  const source = [...deletedProfiles.value].sort((a, b) => {
    return (b.deleted_at ?? "").localeCompare(a.deleted_at ?? "") || profileName(a).localeCompare(profileName(b));
  });
  if (!keyword || browseMode.value !== "trash") return source;
  return source.filter((person) => {
    return (
      profileName(person).toLowerCase().includes(keyword) ||
      person.global_person_id.toLowerCase().includes(keyword)
    );
  });
});

/** 搜索框根据当前模式显示对应提示。 */
const searchPlaceholder = computed(() => {
  if (browseMode.value === "person") return "搜索人物、档案 ID";
  if (browseMode.value === "trash") return "搜索回收站档案";
  return "搜索作品、路径";
});

/** 按搜索词过滤并排序后的作品列表。 */
const filteredVideos = computed(() => {
  const keyword = query.value.trim().toLowerCase();
  const source = [...videos.value].sort((a, b) => {
    return (b.people_count - a.people_count) || videoDisplayTitle(a).localeCompare(videoDisplayTitle(b));
  });
  if (!keyword || browseMode.value !== "work") return source;
  return source.filter((video) => {
    return (
      videoDisplayTitle(video).toLowerCase().includes(keyword) ||
      video.path.toLowerCase().includes(keyword) ||
      video.series_name.toLowerCase().includes(keyword) ||
      (video.original_filename ?? "").toLowerCase().includes(keyword) ||
      (video.source_path ?? "").toLowerCase().includes(keyword) ||
      video.source_directory.toLowerCase().includes(keyword)
    );
  });
});

/** 当前选中的全局人物档案。 */
const selectedProfile = computed(() => {
  return profiles.value.find((person) => person.global_person_id === selectedProfileId.value) ?? null;
});
/** 可合并进当前档案的其他人物档案。 */
const mergeSourceProfiles = computed(() => {
  const currentId = selectedProfileId.value;
  return profiles.value.filter((person) => person.global_person_id !== currentId);
});

/** 将当前人物的观测按作品聚合。 */
const groupedWorks = computed<WorkGroup[]>(() => {
  const groups = new Map<string, WorkGroup>();
  for (const item of observations.value) {
    const title = observationWorkTitle(item);
    const seriesName = item.series_name || "";
    const sourceDirectory = item.source_directory || "";
    const key = `${seriesName}::${sourceDirectory}::${title}`;
    const group =
      groups.get(key) ??
      ({
        key,
        title,
        seriesName,
        sourceDirectory,
        totalDuration: 0,
        items: [],
      } satisfies WorkGroup);
    group.items.push(item);
    group.totalDuration += item.total_duration;
    groups.set(key, group);
  }
  return [...groups.values()].map((group) => ({
    ...group,
    items: [...group.items].sort((a, b) => {
      const hiddenDelta = Number(isHiddenObservation(a)) - Number(isHiddenObservation(b));
      return hiddenDelta || b.detection_count - a.detection_count || a.local_person_id - b.local_person_id;
    }),
  })).sort((a, b) => {
    return a.seriesName.localeCompare(b.seriesName) || a.title.localeCompare(b.title);
  });
});

/** 当前作品内按可见性和检测量排序的人物。 */
const workPeople = computed<PersonItem[]>(() => {
  const source = selectedWork.value?.people ?? [];
  return [...source].sort((a, b) => {
    const hiddenDelta = Number(isHiddenPerson(a)) - Number(isHiddenPerson(b));
    return hiddenDelta || b.detection_count - a.detection_count || a.person_id - b.person_id;
  });
});
/** 当前作品里没有被隐藏的人物，用于统计四视图完成进度。 */
const workVisiblePeople = computed(() => workPeople.value.filter((person) => !isHiddenPerson(person)));
/** 当前作品可见人物数量。 */
const workVisiblePersonCount = computed(() => workVisiblePeople.value.length);
/** 当前人物出现过的作品数量。 */
const workCount = computed(() => groupedWorks.value.length);
/** 当前人物拥有代表脸的观测数量。 */
const referenceCount = computed(() => {
  return observations.value.filter((item) => Boolean(item.representative_face_path)).length;
});
/** 从人物档案观测生成四视图参考候选。 */
const profileReferenceCandidates = computed<ReferenceCandidate[]>(() => {
  return observations.value.flatMap((item) => profileObservationReferenceCandidates(item));
});
/** 从当前作品人物生成四视图参考候选。 */
const workReferenceCandidates = computed<ReferenceCandidate[]>(() => {
  const work = selectedWork.value;
  if (!work) return [];
  return workPeople.value.flatMap((person) => workPersonReferenceCandidates(person));
});
/** 当前作品可用于生成四视图的参考素材总数。 */
const workReferenceCandidateCount = computed(() => workReferenceCandidates.value.length);
/** 当前浏览模式下可见的参考候选。 */
const visibleReferenceCandidates = computed(() => {
  return browseMode.value === "person" ? profileReferenceCandidates.value : workReferenceCandidates.value;
});
/** 当前已选中的参考候选。 */
const selectedReferenceCandidates = computed(() => {
  const byId = new Map(visibleReferenceCandidates.value.map((item) => [item.id, item]));
  return selectedReferenceIds.value
    .map((id) => byId.get(id))
    .filter((item): item is ReferenceCandidate => Boolean(item));
});
/** 当前选择如果只来自同一作品同一人物，就可以直接新建档案并重绑。 */
const selectedLocalPersonTarget = computed<SelectedLocalPersonTarget | null>(() => {
  const candidates = selectedReferenceCandidates.value;
  if (candidates.length === 0) return null;
  const first = candidates[0];
  if (first.videoId === null || first.personId === null) return null;
  const sameLocalPerson = candidates.every((candidate) => {
    return candidate.videoId === first.videoId && candidate.personId === first.personId;
  });
  if (!sameLocalPerson) return null;
  const detail = videoDetailForReferenceCandidate(first);
  const person = detail?.people.find((item) => item.person_id === first.personId) ?? null;
  return {
    videoId: first.videoId,
    personId: first.personId,
    label: person?.label || first.label || "未命名人物",
    workTitle: detail ? videoDisplayTitle(detail) : first.subtitle,
    previousGlobalPersonId: person?.global_person_id ?? first.globalPersonId,
    referenceCount: candidates.length,
  };
});
/** 右侧参考素材栏只展示用户已经勾选的素材。 */
const referenceRailCandidates = computed(() => selectedReferenceCandidates.value);
/** 作品模式下当前选中的人物；跨人物选择时不允许生成。 */
const selectedWorkGenerationPerson = computed(() => {
  if (browseMode.value !== "work") return null;
  const personIds = [...new Set(selectedReferenceCandidates.value.map((item) => item.personId).filter((id): id is number => id !== null))];
  if (personIds.length !== 1) return null;
  return workPeople.value.find((person) => person.person_id === personIds[0]) ?? null;
});
/** 作品顶部优先展示当前选中人物已有资产，没有选中时展示本次会话新生成资产。 */
const workFocusedFourViewAssets = computed<FourViewAsset[]>(() => {
  const person = selectedWorkGenerationPerson.value;
  if (person?.global_person_id) {
    return workFourViewAssetsByGlobalPersonId.value[person.global_person_id] ?? [];
  }
  return generatedWorkFourViewAssets.value;
});
/** 当前作品里已有至少一张四视图资产的人物数量。 */
const workFourViewCompletedPersonCount = computed(() => {
  return workVisiblePeople.value.filter((person) => {
    if (!person.global_person_id) return false;
    return (workFourViewAssetsByGlobalPersonId.value[person.global_person_id]?.length ?? 0) > 0;
  }).length;
});
/** 人物档案模式下默认只预留一组四视图，避免未生成时撑高页面。 */
const profileFourViewSetCount = computed(() => {
  return Math.max(profileFourViewAssets.value.length, 1);
});
/** 作品模式下建议生成的四视图组数。 */
const workFourViewSetCount = computed(() => {
  return clampCount(workVisiblePeople.value.length, 1, 6);
});
const segmentPreviewSegments = computed(() => {
  if (!segmentPreviewWork.value || segmentPreviewPersonId.value === null) return [];
  return segmentPreviewWork.value.segments
    .filter((segment) => segment.person_id === segmentPreviewPersonId.value)
    .sort((a, b) => a.start - b.start);
});
const activeSegmentPreview = computed(() => {
  return segmentPreviewSegments.value[segmentPreviewIndex.value] ?? null;
});
const segmentPreviewPersonLabel = computed(() => {
  const work = segmentPreviewWork.value;
  const personId = segmentPreviewPersonId.value;
  if (!work || personId === null) return "未选择人物";
  return work.people.find((person) => person.person_id === personId)?.label ?? `Person ${personId}`;
});
const segmentPreviewTitle = computed(() => {
  if (!segmentPreviewWork.value) return "人物片段预览";
  return `${segmentPreviewPersonLabel.value} / ${videoDisplayTitle(segmentPreviewWork.value)}`;
});
const segmentPreviewMeta = computed(() => {
  const segment = activeSegmentPreview.value;
  if (!segment) return "没有可播放片段";
  return `${segmentPreviewIndex.value + 1}/${segmentPreviewSegments.value.length} · ${formatDuration(segment.start)} - ${formatDuration(segment.end)}`;
});
const canStepSegmentPreview = computed(() => segmentPreviewSegments.value.length > 1);
const canSubmitManualProfile = computed(() => {
  return Boolean((manualProfileLabel.value.trim().length > 0 || selectedLocalPersonTarget.value) && !isCreatingProfile.value);
});
const canRenameProfile = computed(() => {
  const profile = selectedProfile.value;
  return Boolean(
    profile &&
      profileLabelDraft.value.trim() &&
      profileLabelDraft.value.trim() !== profileName(profile) &&
      !isRenamingProfile.value,
  );
});
const canMergeProfile = computed(() => {
  return Boolean(
    selectedProfileId.value &&
      mergeSourceGlobalPersonId.value &&
      selectedProfileId.value !== mergeSourceGlobalPersonId.value &&
      !isMergingProfile.value,
  );
});

onMounted(loadAll);
watch(
  selectedProfile,
  (profile) => {
    profileLabelDraft.value = profile ? profileName(profile) : "";
  },
  { immediate: true },
);

/** 初始化档案页所需的人物档案和作品数据。 */
async function loadAll() {
  isLoading.value = true;
  errorMessage.value = "";
  try {
    const [nextProfiles, nextDeletedProfiles, nextVideos] = await Promise.all([
      listGlobalPeople({ includeHidden: true }),
      listGlobalPeople({ includeHidden: true, onlyDeleted: true }),
      listVideos(),
    ]);
    profiles.value = nextProfiles;
    deletedProfiles.value = nextDeletedProfiles;
    videos.value = nextVideos;
    if (!selectedProfileId.value || !profiles.value.some((item) => item.global_person_id === selectedProfileId.value)) {
      selectedProfileId.value = profiles.value[0]?.global_person_id ?? null;
    }
    if (!selectedVideoId.value || !videos.value.some((item) => item.id === selectedVideoId.value)) {
      selectedVideoId.value = videos.value[0]?.id ?? null;
    }
    await Promise.all([
      selectedProfileId.value ? loadProfileDetail(selectedProfileId.value) : clearProfileDetail(),
      selectedVideoId.value ? loadWorkDetail(selectedVideoId.value) : Promise.resolve(),
    ]);
  } catch {
    errorMessage.value = "无法读取人物档案数据。";
  } finally {
    isLoading.value = false;
  }
}

/** 切换人物或作品浏览模式。 */
async function setBrowseMode(mode: BrowseMode) {
  browseMode.value = mode;
  query.value = "";
  resetReferenceSelection();
  if (mode === "work" && selectedVideoId.value && !selectedWork.value) {
    await loadWorkDetail(selectedVideoId.value);
  }
}

/** 手动创建一个空白人物档案。 */
async function submitManualProfile() {
  if (selectedLocalPersonTarget.value) {
    await submitProfileFromSelectedReferences();
    return;
  }
  if (!canSubmitManualProfile.value) {
    errorMessage.value = "请先填写人物名称。";
    return;
  }
  errorMessage.value = "";
  statusMessage.value = "";
  isCreatingProfile.value = true;
  try {
    const result = await createManualGlobalPerson(manualProfileLabel.value.trim());
    profiles.value = result.global_people;
    selectedProfileId.value = result.global_person_id;
    browseMode.value = "person";
    manualProfileLabel.value = "";
    resetReferenceSelection();
    await loadProfileDetail(result.global_person_id);
    statusMessage.value = "人物档案已新建";
  } catch {
    errorMessage.value = "无法新建人物档案。";
  } finally {
    isCreatingProfile.value = false;
  }
}

/** 用当前选中的同一作品同一人物参考素材新建档案，并把本地人物重绑过去。 */
async function submitProfileFromSelectedReferences() {
  const target = selectedLocalPersonTarget.value;
  if (!target) {
    errorMessage.value = "请只选择同一作品里的同一个人物后再新建档案。";
    return;
  }
  const label = manualProfileLabel.value.trim() || target.label;
  const previousGlobalPersonId = target.previousGlobalPersonId;
  const sourceFourViewAssets = previousGlobalPersonId ? fourViewAssetsForGlobalId(previousGlobalPersonId) : [];
  errorMessage.value = "";
  statusMessage.value = "";
  isCreatingProfile.value = true;
  try {
    const detail = await createGlobalPersonFromLocal(target.videoId, target.personId, label);
    selectedWork.value = detail;
    selectedVideoId.value = detail.id;
    videoDetailCache.set(detail.id, detail);
    profileVideoDetails.value = {
      ...profileVideoDetails.value,
      [detail.id]: detail,
    };
    let movedAssetCount = 0;
    if (
      previousGlobalPersonId &&
      previousGlobalPersonId !== detail.global_person_id &&
      sourceFourViewAssets.length > 0 &&
      window.confirm(`把原档案里的 ${sourceFourViewAssets.length} 个四视图资产迁移到新档案「${label}」吗？`)
    ) {
      const moveResult = await moveFourViewAssets(previousGlobalPersonId, detail.global_person_id);
      movedAssetCount = moveResult.moved_assets.length;
      profileFourViewAssets.value =
        selectedProfileId.value === previousGlobalPersonId ? moveResult.source_four_view_assets : profileFourViewAssets.value;
      workFourViewAssetsByGlobalPersonId.value = {
        ...workFourViewAssetsByGlobalPersonId.value,
        [previousGlobalPersonId]: moveResult.source_four_view_assets,
        [detail.global_person_id]: moveResult.target_four_view_assets,
      };
      profiles.value = moveResult.global_people;
    } else {
      profiles.value = await listGlobalPeople({ includeHidden: true });
    }
    selectedProfileId.value = detail.global_person_id;
    browseMode.value = "person";
    manualProfileLabel.value = "";
    resetReferenceSelection();
    await loadProfileDetail(detail.global_person_id);
    statusMessage.value = movedAssetCount > 0
      ? `人物档案已新建，并迁移 ${formatCount(movedAssetCount)} 个四视图资产`
      : "人物档案已新建，并已关联所选人物";
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "无法从已选素材新建人物档案。";
  } finally {
    isCreatingProfile.value = false;
  }
}

/** 选中一个全局人物并加载其观测。 */
async function selectProfile(globalPersonId: string) {
  selectedProfileId.value = globalPersonId;
  mergeSourceGlobalPersonId.value = "";
  resetReferenceSelection();
  await loadProfileDetail(globalPersonId);
}

/** 选中一个作品并加载其人物详情。 */
async function selectWork(videoId: number) {
  selectedVideoId.value = videoId;
  generatedWorkFourViewAssets.value = [];
  resetReferenceSelection();
  await loadWorkDetail(videoId);
}

/** 清空人物档案详情。 */
function clearProfileDetail() {
  observations.value = [];
  profileFourViewAssets.value = [];
  profileActions.value = [];
  profileVideoDetails.value = {};
}

/** 读取指定全局人物的观测记录和四视图资产。 */
async function loadProfileDetail(globalPersonId: string) {
  errorMessage.value = "";
  try {
    const [nextObservations, nextAssets, nextActions] = await Promise.all([
      listGlobalObservations(globalPersonId, true),
      listFourViewAssets(globalPersonId),
      listGlobalPersonActions(globalPersonId, 20),
    ]);
    observations.value = nextObservations;
    profileFourViewAssets.value = nextAssets;
    profileActions.value = nextActions;
    await loadProfileVideoDetails(nextObservations);
  } catch {
    clearProfileDetail();
    errorMessage.value = "无法读取人物档案详情。";
  }
}

/** 缓存当前人物档案涉及的作品详情，用于展开该人物在每部作品下的全部截图。 */
async function loadProfileVideoDetails(rows: GlobalObservationItem[]) {
  const videoIds = [...new Set(rows.map((item) => item.video_id).filter((id): id is number => id !== null))];
  const results = await Promise.allSettled(videoIds.map((videoId) => getCachedVideoDetail(videoId)));
  const nextDetails: Record<number, VideoDetail> = {};
  results.forEach((result) => {
    if (result.status === "fulfilled") {
      nextDetails[result.value.id] = result.value;
    }
  });
  profileVideoDetails.value = nextDetails;
}

/** 上传当前人物档案的四视图原图。 */
async function uploadSelectedProfileFourView(file: File) {
  if (!selectedProfileId.value) {
    errorMessage.value = "请先新建或选择一个人物档案。";
    return;
  }
  errorMessage.value = "";
  statusMessage.value = "";
  isUploadingFourViewAsset.value = true;
  try {
    const uploaded = await uploadFourViewAsset(selectedProfileId.value, file, file.name);
    profileFourViewAssets.value = [uploaded, ...profileFourViewAssets.value];
    profiles.value = await listGlobalPeople(true);
    statusMessage.value = "四视图原图已上传";
  } catch {
    errorMessage.value = "无法上传四视图原图，请确认文件是 PNG/JPG/WebP/AVIF。";
  } finally {
    isUploadingFourViewAsset.value = false;
  }
}

/** 删除一张四视图资产，并同步刷新当前页面中的资产列表。 */
async function removeFourViewAsset(asset: FourViewAsset) {
  const confirmed = window.confirm(`确认删除「${asset.label}」？这会移除档案记录，并删除项目上传目录里的图片文件。`);
  if (!confirmed) return;
  errorMessage.value = "";
  statusMessage.value = "";
  try {
    const result = await deleteFourViewAsset(asset.global_person_id, asset.id);
    profiles.value = result.global_people;
    generatedWorkFourViewAssets.value = generatedWorkFourViewAssets.value.filter((item) => item.id !== asset.id);
    workFourViewAssetsByGlobalPersonId.value = {
      ...workFourViewAssetsByGlobalPersonId.value,
      [asset.global_person_id]: result.four_view_assets,
    };
    if (selectedProfileId.value === asset.global_person_id) {
      profileFourViewAssets.value = result.four_view_assets;
      profileActions.value = await listGlobalPersonActions(asset.global_person_id, 20);
    } else {
      profileFourViewAssets.value = profileFourViewAssets.value.filter((item) => item.id !== asset.id);
    }
    selectedFourViewAssetList.value = selectedFourViewAssetList.value.filter((item) => item.id !== asset.id);
    if (selectedFourViewAsset.value?.id === asset.id) {
      closeFourViewAsset();
    } else if (selectedFourViewAsset.value) {
      selectedFourViewAssetIndex.value = Math.max(
        selectedFourViewAssetList.value.findIndex((item) => item.id === selectedFourViewAsset.value?.id),
        0,
      );
    }
    statusMessage.value = "四视图资产已删除";
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "无法删除四视图资产。";
  }
}

/** 保存当前人物档案的展示名称。 */
async function submitRenameSelectedProfile() {
  const profile = selectedProfile.value;
  const nextLabel = profileLabelDraft.value.trim();
  if (!profile || !nextLabel || !canRenameProfile.value) return;
  errorMessage.value = "";
  statusMessage.value = "";
  isRenamingProfile.value = true;
  try {
    const result = await renameGlobalPerson(profile.global_person_id, nextLabel);
    profiles.value = result.global_people;
    selectedProfileId.value = profile.global_person_id;
    profileLabelDraft.value = nextLabel;
    profileActions.value = await listGlobalPersonActions(profile.global_person_id, 20);
    statusMessage.value = "人物档案已重命名";
  } catch {
    errorMessage.value = "无法重命名人物档案。";
  } finally {
    isRenamingProfile.value = false;
  }
}

/** 将当前选中的人物档案移入回收站。 */
async function submitDeleteSelectedProfile() {
  const profile = selectedProfile.value;
  if (!profile) return;
  const confirmed = window.confirm(
    `把人物档案「${profileName(profile)}」移入回收站？这不会删除视频素材、本地识别、四视图和关联，可以从回收站恢复。`,
  );
  if (!confirmed) return;
  errorMessage.value = "";
  statusMessage.value = "";
  isDeletingProfile.value = true;
  try {
    const result = await deleteGlobalPerson(profile.global_person_id);
    profiles.value = result.global_people;
    deletedProfiles.value = result.deleted_global_people;
    const nextProfile = profiles.value[0] ?? null;
    selectedProfileId.value = nextProfile?.global_person_id ?? null;
    mergeSourceGlobalPersonId.value = "";
    resetReferenceSelection();
    if (selectedProfileId.value) {
      await loadProfileDetail(selectedProfileId.value);
    } else {
      clearProfileDetail();
    }
    statusMessage.value = "人物档案已移入回收站";
  } catch {
    errorMessage.value = "无法移入档案回收站。";
  } finally {
    isDeletingProfile.value = false;
  }
}

/** 从回收站恢复人物档案。 */
async function submitRestoreDeletedProfile(profile: GlobalPersonItem) {
  errorMessage.value = "";
  statusMessage.value = "";
  isRestoringProfile.value = true;
  try {
    const result = await restoreGlobalPerson(profile.global_person_id);
    profiles.value = result.global_people;
    deletedProfiles.value = result.deleted_global_people;
    selectedProfileId.value = profile.global_person_id;
    browseMode.value = "person";
    await loadProfileDetail(profile.global_person_id);
    statusMessage.value = "人物档案已恢复";
  } catch {
    errorMessage.value = "无法恢复人物档案。";
  } finally {
    isRestoringProfile.value = false;
  }
}

/** 彻底删除回收站中的人物档案。 */
async function submitPurgeDeletedProfile(profile: GlobalPersonItem) {
  const confirmed = window.confirm(
    `彻底删除人物档案「${profileName(profile)}」？这会解除本地人物关联，并删除观测和四视图资产，不能恢复。`,
  );
  if (!confirmed) return;
  errorMessage.value = "";
  statusMessage.value = "";
  isPurgingProfile.value = true;
  try {
    const result = await purgeGlobalPerson(profile.global_person_id);
    profiles.value = result.global_people;
    deletedProfiles.value = result.deleted_global_people;
    statusMessage.value = "人物档案已彻底删除";
  } catch {
    errorMessage.value = "无法彻底删除人物档案。";
  } finally {
    isPurgingProfile.value = false;
  }
}

/** 把另一个人物档案合并进当前档案。 */
async function submitMergeSelectedProfile() {
  const target = selectedProfile.value;
  const source = profiles.value.find((person) => person.global_person_id === mergeSourceGlobalPersonId.value);
  if (!target || !source || !canMergeProfile.value) return;
  const confirmed = window.confirm(
    `把「${profileName(source)}」合并到「${profileName(target)}」？合并后会保留当前档案，源档案会被删除。`,
  );
  if (!confirmed) return;
  errorMessage.value = "";
  statusMessage.value = "";
  isMergingProfile.value = true;
  try {
    const result = await mergeGlobalPeople(target.global_person_id, source.global_person_id);
    profiles.value = result.global_people;
    observations.value = result.observations;
    profileFourViewAssets.value = result.four_view_assets;
    selectedProfileId.value = target.global_person_id;
    mergeSourceGlobalPersonId.value = "";
    profileActions.value = await listGlobalPersonActions(target.global_person_id, 20);
    resetReferenceSelection();
    statusMessage.value = "人物档案已合并";
  } catch {
    errorMessage.value = "无法合并人物档案。";
  } finally {
    isMergingProfile.value = false;
  }
}

/** 读取指定作品的人物详情。 */
async function loadWorkDetail(videoId: number) {
  errorMessage.value = "";
  try {
    selectedWork.value = await getVideo(videoId);
    videoDetailCache.set(videoId, selectedWork.value);
    await loadWorkFourViewAssets(selectedWork.value.people);
    const firstPerson =
      selectedWork.value.people.find((person) => !isHiddenPerson(person)) ??
      selectedWork.value.people[0] ??
      null;
    if (firstPerson) {
      setSegmentPreview(selectedWork.value, firstPerson.person_id, false);
    }
  } catch {
    selectedWork.value = null;
    workFourViewAssetsByGlobalPersonId.value = {};
    errorMessage.value = "无法读取作品人物记录。";
  }
}

/** 读取当前作品内已关联人物档案的四视图资产。 */
async function loadWorkFourViewAssets(people: PersonItem[]) {
  const globalIds = [
    ...new Set(
      people
        .map((person) => person.global_person_id)
        .filter((id): id is string => Boolean(id)),
    ),
  ];
  const results = await Promise.allSettled(globalIds.map((globalId) => listFourViewAssets(globalId)));
  const nextMap: Record<string, FourViewAsset[]> = {};
  results.forEach((result, index) => {
    if (result.status === "fulfilled") {
      nextMap[globalIds[index]] = result.value;
    }
  });
  workFourViewAssetsByGlobalPersonId.value = nextMap;
}

/** 获取人物档案的展示名称。 */
function profileName(person: GlobalPersonItem) {
  return person.label?.trim() || person.global_person_id;
}

/** 判断本地人物是否被隐藏。 */
function isHiddenPerson(person: { hidden?: number | boolean | null }) {
  return person.hidden === true || Number(person.hidden ?? 0) === 1;
}

/** 判断全局观测是否被隐藏。 */
function isHiddenObservation(item: { hidden?: number | boolean | null }) {
  return item.hidden === true || Number(item.hidden ?? 0) === 1;
}

/** 优先用作品元数据生成视频标题。 */
function videoDisplayTitle(video: VideoItem | VideoDetail) {
  const title = meaningfulTitle(video.title);
  if (title) return title;
  if (video.original_filename) return stripExtension(video.original_filename);
  if (video.source_path) return stripExtension(video.source_path);
  return stripExtension(video.path);
}

/** 为单条观测生成所属作品标题。 */
function observationWorkTitle(item: GlobalObservationItem) {
  const title = meaningfulTitle(item.video_title);
  if (title) return title;
  if (item.original_filename) return stripExtension(item.original_filename);
  if (item.source_path) return stripExtension(item.source_path);
  return stripExtension(item.video_path);
}

/** 过滤空标题和纯哈希文件名。 */
function meaningfulTitle(value: string | null | undefined) {
  const text = value?.trim();
  if (!text) return "";
  const stem = stripExtension(text);
  if (/^(?:[0-9a-f]{16,}|[0-9a-f-]{24,})$/i.test(stem)) return "";
  return stem;
}

/** 去掉路径或文件名中的扩展名。 */
function stripExtension(value: string) {
  const name = value.split(/[\\/]/).filter(Boolean).at(-1) ?? value;
  return name.replace(/\.[^.]+$/, "");
}

/** 生成观测参考素材的稳定 ID。 */
function observationReferenceId(item: GlobalObservationItem) {
  return `observation:${item.id}`;
}

/** 生成作品人物参考素材的稳定 ID。 */
function workPersonReferenceId(person: PersonItem) {
  return `work:${selectedWork.value?.id ?? "none"}:${person.person_id}`;
}

/** 合并同一人物同一帧的候选截图，防止 person/track 代表图重复展示。 */
function dedupeFaceCrops(crops: FaceCropItem[], videoId: number, personId: number | null) {
  const selected = new Map<string, FaceCropItem>();
  for (const crop of crops) {
    const key = faceCropDedupeKey(crop, videoId, personId);
    const current = selected.get(key);
    if (!current || faceCropRank(crop) > faceCropRank(current)) {
      selected.set(key, crop);
    }
  }
  return [...selected.values()];
}

/** 生成候选截图去重键；优先按帧号，缺失帧号时按时间点。 */
function faceCropDedupeKey(crop: FaceCropItem, videoId: number, personId: number | null) {
  if (personId !== null && crop.frame_index !== null) {
    return `person-frame:${videoId}:${personId}:${crop.frame_index}`;
  }
  if (personId !== null && crop.timestamp !== null) {
    return `person-time:${videoId}:${personId}:${crop.timestamp.toFixed(3)}`;
  }
  return `path:${videoId}:${personId ?? "none"}:${crop.path}`;
}

/** 同一帧多条候选时，优先使用带轨迹和置信度的信息。 */
function faceCropRank(crop: FaceCropItem) {
  return (
    (crop.source === "track_representative" ? 1000 : 0) +
    (crop.track_id !== null ? 100 : 0) +
    (crop.confidence ?? -1)
  );
}

/** 获取人物档案在单个作品观测下的逐帧参考素材候选。 */
function profileObservationReferenceCandidates(item: GlobalObservationItem): ReferenceCandidate[] {
  const videoId = item.video_id;
  const detail = videoId === null ? null : profileVideoDetails.value[videoId] ?? null;
  const crops =
    videoId === null
      ? []
      : dedupeFaceCrops(
          detail?.face_crops.filter((crop) => crop.person_id === item.local_person_id) ?? [],
          videoId,
          item.local_person_id,
        )
      .sort((a, b) => {
        return (
          (a.timestamp ?? Number.MAX_SAFE_INTEGER) - (b.timestamp ?? Number.MAX_SAFE_INTEGER) ||
          (a.frame_index ?? Number.MAX_SAFE_INTEGER) - (b.frame_index ?? Number.MAX_SAFE_INTEGER) ||
          a.id - b.id
        );
      });
  if (videoId !== null && crops.length > 0) {
    return crops.slice(0, 48).map((crop) => ({
      id: `observation:${item.id}:crop:${crop.id}`,
      label: item.label,
      subtitle: `${observationWorkTitle(item)} / ${formatCount(item.detection_count)} 框`,
      timeLabel: candidateFrameLabel(crop.frame_index, crop.timestamp),
      facePath: crop.path,
	      frameUrl: workFrameUrl(videoId, crop.frame_index, crop.timestamp),
	      timestamp: crop.timestamp,
	      frameIndex: crop.frame_index,
	      personId: item.local_person_id,
	      videoId,
	      globalPersonId: item.global_person_id,
	      bboxJson: crop.bbox_json,
	      videoWidth: detail?.width ?? null,
	      videoHeight: detail?.height ?? null,
	    }));
	  }
  if (!item.representative_face_path) return [];
  return [
    {
      id: observationReferenceId(item),
      label: item.label,
      subtitle: `${observationWorkTitle(item)} / ${formatDuration(item.total_duration)} / ${formatCount(item.detection_count)} 框`,
      timeLabel: candidateFrameLabel(item.representative_frame_index, item.representative_timestamp),
      facePath: item.representative_face_path,
      frameUrl: videoId === null ? null : workFrameUrl(videoId, item.representative_frame_index, item.representative_timestamp),
      timestamp: item.representative_timestamp,
	      frameIndex: item.representative_frame_index,
	      personId: item.local_person_id,
	      videoId,
	      globalPersonId: item.global_person_id,
	      bboxJson: null,
	      videoWidth: detail?.width ?? null,
	      videoHeight: detail?.height ?? null,
	    },
	  ];
}

/** 获取作品人物的逐帧参考素材候选。 */
function workPersonReferenceCandidates(person: PersonItem): ReferenceCandidate[] {
  const work = selectedWork.value;
  if (!work) return [];
  const crops = dedupeFaceCrops(
    work.face_crops.filter((crop) => crop.person_id === person.person_id),
    work.id,
    person.person_id,
  )
    .sort((a, b) => {
      return (
        (a.timestamp ?? Number.MAX_SAFE_INTEGER) - (b.timestamp ?? Number.MAX_SAFE_INTEGER) ||
        (a.frame_index ?? Number.MAX_SAFE_INTEGER) - (b.frame_index ?? Number.MAX_SAFE_INTEGER) ||
        a.id - b.id
      );
    });
  const candidates = crops.map((crop) => {
    const frameUrl = workFrameUrl(work.id, crop.frame_index, crop.timestamp);
    return {
      id: `work:${work.id}:${person.person_id}:crop:${crop.id}`,
      label: person.label,
      subtitle: `${candidateFrameLabel(crop.frame_index, crop.timestamp)} / ${videoDisplayTitle(work)}`,
      timeLabel: candidateFrameLabel(crop.frame_index, crop.timestamp),
      facePath: crop.path,
      frameUrl,
      timestamp: crop.timestamp,
	      frameIndex: crop.frame_index,
	      personId: person.person_id,
	      videoId: work.id,
	      globalPersonId: person.global_person_id,
	      bboxJson: crop.bbox_json,
	      videoWidth: work.width,
	      videoHeight: work.height,
	    };
	  });
  if (candidates.length > 0) return candidates.slice(0, 48);
  const frameUrl = workFrameUrl(work.id, person.representative_frame_index, person.representative_timestamp);
  return [
    {
      id: workPersonReferenceId(person),
      label: person.label,
      subtitle: `${candidateFrameLabel(person.representative_frame_index, person.representative_timestamp)} / 代表帧`,
      timeLabel: candidateFrameLabel(person.representative_frame_index, person.representative_timestamp),
      facePath: person.representative_face_path,
      frameUrl,
      timestamp: person.representative_timestamp,
	      frameIndex: person.representative_frame_index,
	      personId: person.person_id,
	      videoId: work.id,
	      globalPersonId: person.global_person_id,
	      bboxJson: null,
	      videoWidth: work.width,
	      videoHeight: work.height,
	    },
  ];
}

/** 根据参考素材找到已缓存的视频详情。 */
function videoDetailForReferenceCandidate(candidate: ReferenceCandidate) {
  const videoId = candidate.videoId;
  if (videoId === null) return null;
  if (selectedWork.value?.id === videoId) return selectedWork.value;
  return profileVideoDetails.value[videoId] ?? videoDetailCache.get(videoId) ?? null;
}

/** 生成完整视频帧 URL；没有帧定位信息时返回空。 */
function workFrameUrl(videoId: number, frameIndex: number | null | undefined, timestamp: number | null | undefined) {
  if (frameIndex == null && timestamp == null) return null;
  return videoFrameUrl(videoId, { frameIndex, timestamp });
}

/** 生成候选素材对应的帧标识。 */
function candidateFrameLabel(frameIndex: number | null | undefined, timestamp: number | null | undefined) {
  const parts: string[] = [];
  if (timestamp !== null && timestamp !== undefined) parts.push(formatDuration(timestamp));
  if (frameIndex !== null && frameIndex !== undefined) parts.push(`#${frameIndex}`);
  return parts.join(" / ") || "未知帧";
}

/** 获取按人物模式下某部作品里的全部参考帧候选。 */
function profileWorkCandidates(work: WorkGroup) {
  return work.items.flatMap((item) => profileObservationReferenceCandidates(item));
}

/** 批量选中参考素材；replace=true 时会先清掉跨人物旧选择。 */
function selectReferenceCandidates(candidates: ReferenceCandidate[], replace = false) {
  const nextIds = replace ? new Set<string>() : new Set(selectedReferenceIds.value);
  for (const candidate of candidates) {
    nextIds.add(candidate.id);
  }
  selectedReferenceIds.value = [...nextIds];
  if (candidates[0]) {
    void previewReferenceCandidate(candidates[0], false);
  }
}

/** 全选当前人物档案下的所有参考帧。 */
function selectAllProfileReferences() {
  selectReferenceCandidates(profileReferenceCandidates.value, true);
}

/** 全选当前人物档案在某部作品里的某一个本地人物参考帧。 */
function selectAllProfileObservationReferences(item: GlobalObservationItem) {
  selectReferenceCandidates(profileObservationReferenceCandidates(item), true);
}

/** 全选当前人物在某部作品里的参考帧。 */
function selectAllProfileWorkReferences(work: WorkGroup) {
  selectReferenceCandidates(profileWorkCandidates(work));
}

/** 全选作品模式下某一个人物的参考帧；会替换掉其他人物的旧选择。 */
function selectAllWorkPersonReferences(person: PersonItem) {
  selectReferenceCandidates(workPersonReferenceCandidates(person), true);
}

/** 统计某组候选素材里已经被选中的数量。 */
function selectedReferenceCount(candidates: ReferenceCandidate[]) {
  const selected = new Set(selectedReferenceIds.value);
  return candidates.filter((candidate) => selected.has(candidate.id)).length;
}

/** 切换任意参考帧候选的选中状态。 */
function toggleReferenceCandidate(candidate: ReferenceCandidate) {
  toggleReferenceSelection(candidate.id);
  void previewReferenceCandidate(candidate, false);
}

/** 用候选帧定位右侧人物片段预览。 */
async function previewReferenceCandidate(candidate: ReferenceCandidate, autoplay = true) {
  if (candidate.videoId === null || candidate.personId === null) return;
  segmentPreviewLoading.value = true;
  segmentPreviewError.value = "";
  try {
    const work = selectedWork.value?.id === candidate.videoId
      ? selectedWork.value
      : await getCachedVideoDetail(candidate.videoId);
    setSegmentPreview(work, candidate.personId, autoplay, candidate.timestamp);
  } catch {
    segmentPreviewError.value = "无法读取这个人物的片段";
  } finally {
    segmentPreviewLoading.value = false;
  }
}

/** 判断参考素材是否已被选中。 */
function isReferenceSelected(referenceId: string) {
  return selectedReferenceIds.value.includes(referenceId);
}

/** 切换参考素材的选中状态。 */
function toggleReferenceSelection(referenceId: string) {
  selectedReferenceIds.value = isReferenceSelected(referenceId)
    ? selectedReferenceIds.value.filter((id) => id !== referenceId)
    : [...selectedReferenceIds.value, referenceId];
}

/** 打开一张参考素材的大图预览。 */
function openReferenceCandidate(candidate: ReferenceCandidate) {
  selectedReferenceCandidate.value = candidate;
}

/** 关闭参考素材大图预览。 */
function closeReferenceCandidate() {
  selectedReferenceCandidate.value = null;
}

/** 清空参考素材选择并停止预览轮播。 */
function resetReferenceSelection() {
  selectedReferenceIds.value = [];
  selectedReferenceCandidate.value = null;
}

/** 获取作品人物已拥有的四视图资产。 */
function fourViewAssetsForWorkPerson(person: PersonItem) {
  if (!person.global_person_id) return [];
  return workFourViewAssetsByGlobalPersonId.value[person.global_person_id] ?? [];
}

/** 获取当前页面已加载的某个档案四视图资产。 */
function fourViewAssetsForGlobalId(globalPersonId: string) {
  if (selectedProfileId.value === globalPersonId) return profileFourViewAssets.value;
  return workFourViewAssetsByGlobalPersonId.value[globalPersonId] ?? [];
}

/** 根据当前浏览模式确定四视图生成应挂到哪个人物档案。 */
async function ensureGenerationTargetGlobalPersonId(candidates: ReferenceCandidate[]) {
  if (browseMode.value === "person") {
    return selectedProfileId.value;
  }
  if (!selectedWork.value) {
    statusMessage.value = "请先选择作品";
    return null;
  }
  const personIds = [...new Set(candidates.map((item) => item.personId).filter((id): id is number => id !== null))];
  if (personIds.length !== 1) {
    statusMessage.value = "按作品生成时，请只选择同一个人物的参考帧";
    return null;
  }
  const person = selectedWork.value.people.find((item) => item.person_id === personIds[0]);
  if (!person) {
    statusMessage.value = "无法定位选中的本地人物";
    return null;
  }
  if (person.global_person_id) {
    return person.global_person_id;
  }
  const detail = await createGlobalPersonFromLocal(selectedWork.value.id, person.person_id, person.label);
  selectedWork.value = detail;
  videoDetailCache.set(detail.id, detail);
  return detail.global_person_id;
}

/** 把前端候选帧转换成后端生成请求中的参考素材。 */
function referenceCandidateToInput(candidate: ReferenceCandidate): FourViewReferenceInput {
  return {
    video_id: candidate.videoId,
    frame_index: candidate.frameIndex,
    timestamp: candidate.timestamp,
    face_path: candidate.facePath,
    label: candidate.label,
  };
}

/** 生成资产默认名称。 */
function generationTargetLabel(candidates: ReferenceCandidate[]) {
  return candidates[0]?.label?.trim() || (selectedProfile.value ? profileName(selectedProfile.value) : "人物");
}

/** 将数量限制在指定范围内。 */
function clampCount(value: number, min: number, max: number) {
  return Math.min(Math.max(Math.round(value), min), max);
}

/** 限制视频时间在有效范围内。 */
function clampTime(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

async function openObservationSegmentPreview(item: GlobalObservationItem, autoplay: boolean) {
  if (item.video_id === null) {
    segmentPreviewError.value = "这条观测缺少作品记录";
    return;
  }
  segmentPreviewLoading.value = true;
  segmentPreviewError.value = "";
  try {
    const work = await getCachedVideoDetail(item.video_id);
    setSegmentPreview(work, item.local_person_id, autoplay, item.representative_timestamp);
  } catch {
    segmentPreviewError.value = "无法读取这个人物的片段";
  } finally {
    segmentPreviewLoading.value = false;
  }
}

function openWorkPersonSegmentPreview(person: PersonItem, autoplay: boolean) {
  if (!selectedWork.value) return;
  setSegmentPreview(selectedWork.value, person.person_id, autoplay);
}

async function getCachedVideoDetail(videoId: number) {
  const cached = videoDetailCache.get(videoId);
  if (cached) return cached;
  const detail = await getVideo(videoId);
  videoDetailCache.set(videoId, detail);
  return detail;
}

function setSegmentPreview(work: VideoDetail, personId: number, autoplay: boolean, targetTime: number | null = null) {
  const sameTarget = segmentPreviewWork.value?.id === work.id && segmentPreviewPersonId.value === personId;
  segmentPreviewWork.value = work;
  segmentPreviewPersonId.value = personId;
  const segments = work.segments
    .filter((segment) => segment.person_id === personId)
    .sort((a, b) => a.start - b.start);
  if (targetTime !== null) {
    const containingIndex = segments.findIndex((segment) => targetTime >= segment.start && targetTime <= segment.end);
    const nearestIndex = segments.reduce((bestIndex, segment, index) => {
      const best = segments[bestIndex];
      if (!best) return index;
      const currentDistance = Math.min(Math.abs(targetTime - segment.start), Math.abs(targetTime - segment.end));
      const bestDistance = Math.min(Math.abs(targetTime - best.start), Math.abs(targetTime - best.end));
      return currentDistance < bestDistance ? index : bestIndex;
    }, 0);
    segmentPreviewIndex.value = containingIndex >= 0 ? containingIndex : nearestIndex;
    segmentPreviewTargetTime.value = clampTime(targetTime, 0, work.duration_seconds);
  } else {
    if (!sameTarget) {
      segmentPreviewIndex.value = 0;
    }
    segmentPreviewTargetTime.value = null;
  }
  void nextTick(() => syncSegmentPreviewVideo(autoplay));
}

async function syncSegmentPreviewVideo(autoplay: boolean) {
  const video = segmentPreviewPanelRef.value?.getVideoElement() ?? null;
  const segment = activeSegmentPreview.value;
  if (!video || !segment) return;
  video.currentTime = segmentPreviewSeekTime(segment);
  if (!autoplay) {
    video.pause();
    return;
  }
  video.muted = true;
  try {
    await video.play();
  } catch {
    segmentPreviewError.value = "浏览器阻止自动播放，可点击播放";
  }
}

function stepSegmentPreview(delta: number) {
  const count = segmentPreviewSegments.value.length;
  if (count === 0) return;
  segmentPreviewTargetTime.value = null;
  segmentPreviewIndex.value = (segmentPreviewIndex.value + delta + count) % count;
  void nextTick(() => syncSegmentPreviewVideo(true));
}

function segmentPreviewSeekTime(segment: SegmentItem) {
  const duration = segmentPreviewWork.value?.duration_seconds ?? segment.end;
  if (segmentPreviewTargetTime.value !== null) {
    return clampTime(segmentPreviewTargetTime.value, 0, duration);
  }
  return Math.min(Math.max(segment.start - segmentPreviewLeadSeconds, 0), duration);
}

async function queueFourViewGeneration() {
  if (selectedReferenceIds.value.length === 0) {
    statusMessage.value = "请先选择参考素材";
    return;
  }
  const selectedCandidates = selectedReferenceCandidates.value;
  if (selectedCandidates.length === 0) {
    statusMessage.value = "当前选择的参考素材已过期，请重新选择";
    return;
  }
  errorMessage.value = "";
  statusMessage.value = "";
  isGeneratingFourViewAsset.value = true;
  try {
    const targetGlobalPersonId = await ensureGenerationTargetGlobalPersonId(selectedCandidates);
    if (!targetGlobalPersonId) return;
    const generated = await generateFourViewAsset(targetGlobalPersonId, {
      label: `${generationTargetLabel(selectedCandidates)} 四视图`,
      references: selectedCandidates.slice(0, 8).map(referenceCandidateToInput),
    });
    if (browseMode.value === "person" && selectedProfileId.value === targetGlobalPersonId) {
      profileFourViewAssets.value = [generated, ...profileFourViewAssets.value];
      profileActions.value = await listGlobalPersonActions(targetGlobalPersonId, 20);
    } else {
      generatedWorkFourViewAssets.value = [generated, ...generatedWorkFourViewAssets.value];
      workFourViewAssetsByGlobalPersonId.value = {
        ...workFourViewAssetsByGlobalPersonId.value,
        [targetGlobalPersonId]: [generated, ...(workFourViewAssetsByGlobalPersonId.value[targetGlobalPersonId] ?? [])],
      };
    }
    profiles.value = await listGlobalPeople(true);
    selectedFourViewAsset.value = generated;
    selectedFourViewAssetList.value = [generated];
    selectedFourViewAssetIndex.value = 0;
    statusMessage.value = `四视图已生成：${generated.image_path}`;
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? error.message
        : "无法生成四视图。请确认 configs/ai.toml 已启用大模型和图像生成，并且接口地址、Key、模型可用。";
  } finally {
    isGeneratingFourViewAsset.value = false;
  }
}

/** 打开已生成四视图的未切分原图预览，并记录同组资产用于左右切换。 */
function openFourViewAsset(asset: FourViewAsset, index?: number, assets?: FourViewAsset[]) {
  if (!asset.image_path) return;
  const previewableAssets = (assets?.length ? assets : [asset]).filter((item) => Boolean(item.image_path));
  const requestedIndex = previewableAssets.findIndex((item) => item.id === asset.id);
  const fallbackIndex = typeof index === "number" ? Math.min(Math.max(index, 0), previewableAssets.length - 1) : 0;
  selectedFourViewAssetList.value = previewableAssets;
  selectedFourViewAssetIndex.value = requestedIndex >= 0 ? requestedIndex : fallbackIndex;
  selectedFourViewAsset.value = previewableAssets[selectedFourViewAssetIndex.value] ?? asset;
}

/** 关闭四视图原图预览。 */
function closeFourViewAsset() {
  selectedFourViewAsset.value = null;
  selectedFourViewAssetList.value = [];
  selectedFourViewAssetIndex.value = 0;
}

/** 在当前四视图预览组里循环切换。 */
function showAdjacentFourViewAsset(direction: -1 | 1) {
  const assets = selectedFourViewAssetList.value;
  if (assets.length <= 1) return;
  const nextIndex = (selectedFourViewAssetIndex.value + direction + assets.length) % assets.length;
  selectedFourViewAssetIndex.value = nextIndex;
  selectedFourViewAsset.value = assets[nextIndex] ?? null;
}

function showPreviousFourViewAsset() {
  showAdjacentFourViewAsset(-1);
}

function showNextFourViewAsset() {
  showAdjacentFourViewAsset(1);
}

/** 切换作品内人物的隐藏状态并刷新档案数据。 */
async function toggleWorkPersonHidden(person: PersonItem) {
  if (!selectedWork.value) return;
  errorMessage.value = "";
  try {
    selectedWork.value = await setPersonHidden(
      selectedWork.value.id,
      person.person_id,
      !isHiddenPerson(person),
    );
    const [nextProfiles, nextVideos] = await Promise.all([
      listGlobalPeople(true),
      listVideos(),
    ]);
    profiles.value = nextProfiles;
	    videos.value = nextVideos;
	    if (selectedProfileId.value) {
	      await loadProfileDetail(selectedProfileId.value);
	    }
  } catch {
    errorMessage.value = "无法更新人物显示状态。";
  }
}

/** 格式化档案页中的数量。 */
function formatCount(value: number) {
  return numberFormatter.format(value);
}

/** 格式化档案页中的小数。 */
function formatDecimal(value: number) {
  return decimalFormatter.format(value);
}

/** 格式化档案页中的时长。 */
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
</script>

<style scoped>
.profiles-page {
  grid-template-columns: 340px minmax(0, 1fr);
  height: calc(100dvh - 48px);
  max-height: calc(100dvh - 48px);
}

.appearance-tile {
  min-width: 0;
}

.profile-list,
.profile-scroll-area {
  scrollbar-gutter: stable;
}

.profile-preview-rail {
  align-self: start;
}

@media (min-width: 1280px) {
  .profile-preview-rail {
    position: sticky;
    top: 0;
    max-height: calc(100dvh - 48px);
    overflow-y: auto;
    scrollbar-gutter: stable;
  }
}

@media (max-width: 980px) {
  .profiles-page {
    height: calc(100dvh - 48px);
    max-height: none;
    grid-template-columns: 1fr;
    overflow-y: auto;
  }

  .profile-list {
    max-height: 320px;
  }
}
</style>

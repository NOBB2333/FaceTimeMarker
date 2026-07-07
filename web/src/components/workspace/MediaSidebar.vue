<template>
  <aside class="media-panel flex min-h-0 min-w-0 flex-col overflow-hidden border-r border-white/10 bg-[#0f1319]">
    <div class="border-b border-white/10 px-4 py-4">
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0">
          <h2 class="text-sm font-semibold text-[#f8fafc]">素材</h2>
          <p class="mt-1 text-xs text-[#7d8998]">
            {{ formatCount(filteredVideos.length) }} / {{ formatCount(videos.length) }} 个分析结果
          </p>
        </div>
        <Database class="mt-0.5 h-4 w-4 text-[#34d5c8]" aria-hidden="true" />
      </div>
    </div>

    <div class="grid grid-cols-3 border-b border-white/10 bg-[#0a0d12] p-1">
      <button
        class="h-8 text-xs font-semibold transition-colors duration-150 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]"
        :class="activeSidebarTab === 'library' ? 'bg-[#34d5c8] text-[#061211]' : 'text-[#8f9bac] hover:text-[#eef2f7]'"
        type="button"
        @click="activeSidebarTab = 'library'"
      >
        素材库
      </button>
      <button
        class="h-8 text-xs font-semibold transition-colors duration-150 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]"
        :class="activeSidebarTab === 'import' ? 'bg-[#34d5c8] text-[#061211]' : 'text-[#8f9bac] hover:text-[#eef2f7]'"
        type="button"
        @click="activeSidebarTab = 'import'"
      >
        导入
      </button>
      <button
        class="h-8 text-xs font-semibold transition-colors duration-150 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]"
        :class="activeSidebarTab === 'trash' ? 'bg-[#34d5c8] text-[#061211]' : 'text-[#8f9bac] hover:text-[#eef2f7]'"
        type="button"
        @click="activeSidebarTab = 'trash'"
      >
        回收站
      </button>
    </div>

    <div
      v-if="isBusy"
      class="progress-panel border-b border-white/10 bg-[#0a0d12] px-4 py-3"
      role="status"
      aria-live="polite"
    >
      <div class="flex items-center justify-between gap-3">
        <span class="truncate text-xs font-semibold text-[#f8fafc]">{{ busyLabel }}</span>
        <span class="flex shrink-0 items-center gap-2">
          <span class="timecode text-xs text-[#f5c451]">
            {{ formatCount(operationProgressPercent) }}%
          </span>
          <button
            v-if="canCancelAnalysis"
            class="inline-flex h-7 items-center gap-1.5 border border-[#7f2e2e] bg-[#2a1215] px-2 text-[11px] font-semibold text-[#fecaca] transition-colors duration-150 hover:bg-[#35171b] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#f87171]"
            type="button"
            @click="$emit('cancelAnalysis')"
          >
            <Square class="h-3.5 w-3.5" aria-hidden="true" />
            终止
          </button>
        </span>
      </div>
      <div class="mt-2 h-1.5 overflow-hidden bg-black/50">
        <div
          class="progress-fill h-full bg-[#34d5c8]"
          :style="{ width: `${operationProgressPercent}%` }"
        />
      </div>
      <div class="mt-2 flex items-center justify-between gap-3 text-[11px] text-[#7d8998]">
        <span class="truncate">{{ operationProgressMessage }}</span>
        <span class="timecode shrink-0">{{ analysisElapsedLabel }}</span>
      </div>
    </div>

    <div v-if="activeSidebarTab === 'library'" class="flex min-h-0 flex-1 flex-col">
      <div class="border-b border-white/10 p-4">
        <label class="flex h-9 items-center gap-2 border border-white/10 bg-[#0a0d12] px-3 focus-within:border-[#34d5c8]/70">
          <Search class="h-4 w-4 text-[#697586]" aria-hidden="true" />
          <span class="sr-only">搜索视频</span>
          <input
            :value="videoQuery"
            autocomplete="off"
            class="min-w-0 flex-1 bg-transparent text-sm text-[#eef2f7] placeholder:text-[#536171] focus-visible:outline-none"
            name="videoQuery"
            placeholder="搜索标题、系列、路径"
            @input="$emit('update:videoQuery', ($event.target as HTMLInputElement).value)"
          />
        </label>
      </div>

      <div class="min-h-0 flex-1 overflow-y-auto">
        <div
          v-for="video in filteredVideos"
          :key="video.id"
          class="group grid grid-cols-[minmax(0,1fr)_34px] gap-2 border-b border-white/10 px-4 py-4 transition-colors duration-150 hover:bg-[#151c24]"
          :class="selectedVideoId === video.id ? 'bg-[#16232a]' : ''"
        >
          <button
            class="min-w-0 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]"
            type="button"
            @click="$emit('selectVideo', video.id)"
          >
          <span class="flex items-start gap-3">
            <span class="mt-0.5 grid h-10 w-10 shrink-0 place-items-center border border-white/10 bg-[#0a0d12] text-[#7d8998] group-hover:text-[#34d5c8]">
              <FileVideo class="h-5 w-5" aria-hidden="true" />
            </span>
            <span class="min-w-0 flex-1">
              <span class="block truncate text-sm font-semibold text-[#f8fafc]">
                {{ videoDisplayTitle(video) }}
              </span>
              <span class="mt-1 block truncate text-xs text-[#536171]">
                {{ videoSourceLine(video) }}
              </span>
              <span class="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-[#7d8998]">
                <span v-if="video.series_name" class="text-[#f5c451]">{{ video.series_name }}</span>
                <span>{{ formatCount(video.people_count) }} 人物</span>
                <span class="timecode">{{ formatTime(video.duration_seconds) }}</span>
                <span v-if="video.analysis_elapsed_seconds !== null" class="timecode text-[#34d5c8]">
                  耗时 {{ formatTime(video.analysis_elapsed_seconds) }}
                </span>
                <span>{{ video.width }} x {{ video.height }}</span>
              </span>
              <span class="mt-3 block h-1 bg-black/35">
                <span
                  class="block h-full bg-[#34d5c8]"
                  :style="{ width: `${Math.min(video.people_count * 12, 100)}%` }"
                />
              </span>
            </span>
          </span>
          </button>
          <button
            class="mt-0.5 grid h-8 w-8 place-items-center border border-white/10 bg-[#151b23] text-[#8f9bac] transition-colors duration-150 hover:border-[#f87171]/60 hover:text-[#fecaca] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#f87171]"
            type="button"
            aria-label="移入回收站"
            title="移入回收站"
            @click="$emit('trashVideo', video.id)"
          >
            <Trash2 class="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        <div v-if="videos.length === 0" class="px-4 py-10 text-sm text-[#7d8998]">
          暂无分析结果。
        </div>
        <div v-else-if="filteredVideos.length === 0" class="px-4 py-10 text-sm text-[#7d8998]">
          没有匹配的视频。
        </div>
      </div>
    </div>

    <div v-else-if="activeSidebarTab === 'trash'" class="min-h-0 flex-1 overflow-y-auto">
      <div
        v-for="video in trashVideos"
        :key="video.id"
        class="border-b border-white/10 px-4 py-4"
      >
        <div class="flex items-start gap-3">
          <span class="mt-0.5 grid h-10 w-10 shrink-0 place-items-center border border-white/10 bg-[#0a0d12] text-[#7d8998]">
            <FileVideo class="h-5 w-5" aria-hidden="true" />
          </span>
          <span class="min-w-0 flex-1">
            <span class="block truncate text-sm font-semibold text-[#f8fafc]">
              {{ videoDisplayTitle(video) }}
            </span>
            <span class="mt-1 block truncate text-xs text-[#536171]">
              {{ videoSourceLine(video) }}
            </span>
            <span class="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-[#7d8998]">
              <span>{{ formatCount(video.people_count) }} 人物</span>
              <span class="timecode">{{ formatTime(video.duration_seconds) }}</span>
              <span v-if="video.deleted_at" class="text-[#f5c451]">已移入回收站</span>
            </span>
          </span>
        </div>
        <div class="mt-3 grid grid-cols-2 gap-2">
          <button
            class="inline-flex h-8 items-center justify-center gap-2 border border-[#34d5c8]/40 bg-[#112226] px-2 text-xs font-semibold text-[#74f2e8] transition-colors duration-150 hover:bg-[#173039] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]"
            type="button"
            @click="$emit('restoreVideo', video.id)"
          >
            <RotateCcw class="h-4 w-4" aria-hidden="true" />
            还原
          </button>
          <button
            class="inline-flex h-8 items-center justify-center gap-2 border border-[#7f2e2e] bg-[#2a1215] px-2 text-xs font-semibold text-[#fecaca] transition-colors duration-150 hover:bg-[#35171b] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#f87171]"
            type="button"
            @click="$emit('purgeVideo', video.id)"
          >
            <Trash2 class="h-4 w-4" aria-hidden="true" />
            彻底删除
          </button>
        </div>
      </div>
      <div v-if="trashVideos.length === 0" class="px-4 py-10 text-sm text-[#7d8998]">
        回收站为空。
      </div>
    </div>

    <div v-else class="min-h-0 flex-1 overflow-y-auto p-4">
      <div class="space-y-3 pb-8">
        <label
          class="drop-zone group relative block cursor-pointer border border-dashed border-[#2f3b49] bg-[#0a0d12] p-4 transition-colors duration-150 hover:border-[#34d5c8]/70 hover:bg-[#0d1519]"
          :class="isDragging ? 'border-[#34d5c8] bg-[#0d181b]' : ''"
          for="videoFile"
          @dragenter.prevent="handleDragEnter"
          @dragover.prevent="handleDragOver"
          @dragleave="handleDragLeave"
          @drop.prevent="handleDrop"
        >
          <input
            id="videoFile"
            ref="fileInputEl"
            class="sr-only"
            type="file"
            accept=".mp4,.mov,.mkv,.avi,.webm,.m4v,video/*"
            multiple
            @change="handleFileInput"
          />
          <span class="flex items-center gap-3">
            <span class="grid h-11 w-11 shrink-0 place-items-center border border-[#34d5c8]/30 bg-[#34d5c8]/10 text-[#34d5c8]">
              <Upload v-if="!isBusy" class="h-5 w-5" aria-hidden="true" />
              <Loader2 v-else class="h-5 w-5 animate-spin" aria-hidden="true" />
            </span>
            <span class="min-w-0">
              <span class="block text-sm font-semibold text-[#f8fafc]">
                {{ isBusy ? "追加到队列" : "上传视频" }}
              </span>
              <span class="mt-1 block truncate text-xs text-[#7d8998]">
                {{ pendingImportCount > 0 ? `队列 ${formatCount(pendingImportCount)} 个` : "MP4 / MOV / MKV / AVI / WEBM" }}
              </span>
            </span>
          </span>
        </label>

        <div class="analysis-settings grid gap-2 border border-white/10 bg-[#0a0d12] p-3">
          <div class="flex items-center justify-between gap-3">
            <span class="flex min-w-0 items-center gap-2 text-xs font-semibold text-[#cbd5e1]">
              <Settings2 class="h-4 w-4 text-[#34d5c8]" aria-hidden="true" />
              分析参数
            </span>
            <button
              class="h-7 border px-2 text-[11px] font-semibold transition-colors duration-150 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]"
              :class="useCache
                ? 'border-white/10 bg-[#151b23] text-[#cbd5e1] hover:border-[#34d5c8]/60'
                : 'border-[#f5c451]/50 bg-[#2a2414] text-[#f5c451]'"
              type="button"
              :disabled="isBusy"
              :aria-pressed="!useCache"
              @click="$emit('update:useCache', !useCache)"
            >
              {{ useCache ? "使用缓存" : "重新识别" }}
            </button>
          </div>
          <label class="grid gap-1">
            <span class="text-xs text-[#8f9bac]">系列/作品</span>
            <input
              :value="seriesName"
              autocomplete="off"
              class="h-8 border border-white/10 bg-[#05070a] px-2 text-sm text-[#eef2f7] placeholder:text-[#536171] focus-visible:border-[#34d5c8] focus-visible:outline-none"
              name="seriesName"
              placeholder="例如 第一季 / 电影合集"
              :disabled="isBusy"
              @input="$emit('update:seriesName', ($event.target as HTMLInputElement).value)"
            />
          </label>
          <label class="grid gap-1">
            <span class="flex items-center justify-between gap-2">
              <span class="text-xs text-[#8f9bac]">配置文件</span>
              <span class="truncate text-[11px] text-[#536171]">留空用默认</span>
            </span>
            <input
              :value="configPath"
              autocomplete="off"
              class="h-8 border border-white/10 bg-[#05070a] px-2 text-sm text-[#eef2f7] placeholder:text-[#536171] focus-visible:border-[#34d5c8] focus-visible:outline-none"
              name="configPath"
              placeholder="configs/profiles/anime-lowres-strict.toml"
              :disabled="isBusy"
              @input="$emit('update:configPath', ($event.target as HTMLInputElement).value)"
            />
          </label>
          <label class="grid grid-cols-[minmax(0,1fr)_88px] items-center gap-2">
            <span class="min-w-0">
              <span class="block text-xs text-[#8f9bac]">预设人数</span>
              <span class="block truncate text-[11px] text-[#536171]">留空为 Auto</span>
            </span>
            <input
              :value="expectedPeopleCount ?? ''"
              class="h-8 min-w-0 border border-white/10 bg-[#05070a] px-2 text-sm text-[#eef2f7] placeholder:text-[#536171] focus-visible:border-[#34d5c8] focus-visible:outline-none"
              inputmode="numeric"
              min="1"
              name="expectedPeopleCount"
              placeholder="Auto"
              step="1"
              type="number"
              :disabled="isBusy"
              @input="handleExpectedPeopleCountInput"
            />
          </label>
          <div class="grid gap-2 border-t border-white/10 pt-2">
            <label class="grid gap-1">
              <span class="flex items-center justify-between gap-2">
                <span class="flex min-w-0 items-center gap-2 text-xs text-[#8f9bac]">
                  <Cpu class="h-4 w-4 text-[#34d5c8]" aria-hidden="true" />
                  硬件加速
                </span>
                <span class="truncate text-[11px] text-[#536171]">
                  推荐 {{ recommendedHardwareLabel }}
                </span>
              </span>
              <select
                :value="hardwareProfile"
                class="h-8 w-full border border-white/10 bg-[#05070a] px-2 text-sm text-[#eef2f7] focus-visible:border-[#34d5c8] focus-visible:outline-none"
                :disabled="isBusy"
                @change="handleHardwareProfileInput"
              >
                <option
                  v-for="profile in hardwareProfiles"
                  :key="profile.id"
                  :value="profile.id"
                >
                  {{ profile.label }}{{ profile.available ? "" : "（未启用）" }}
                </option>
              </select>
            </label>
            <label class="flex h-8 items-center justify-between gap-3 border border-white/10 bg-[#05070a] px-2">
              <span class="truncate text-xs text-[#cbd5e1]">允许失败时 CPU 降级</span>
              <input
                class="h-4 w-4 accent-[#34d5c8]"
                type="checkbox"
                :checked="allowCpuFallback"
                :disabled="isBusy"
                @change="handleCpuFallbackInput"
              />
            </label>
            <div class="grid gap-1 text-[11px] leading-4 text-[#7d8998]">
              <span class="truncate">当前：{{ selectedHardwareNote }}</span>
              <span class="truncate">Provider：{{ availableProviderLabel }}</span>
              <span v-if="gpuDeviceLabel" class="truncate">GPU：{{ gpuDeviceLabel }}</span>
            </div>
          </div>
          <button
            class="inline-flex h-8 items-center justify-center gap-2 border border-white/10 bg-[#151b23] px-3 text-xs font-semibold text-[#cbd5e1] transition-colors duration-150 hover:border-[#f5c451]/60 hover:text-[#f5c451] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#f5c451]"
            type="button"
            :disabled="isBusy || !canReanalyzeSelected"
            @click="$emit('reanalyzeSelected')"
          >
            <RotateCcw class="h-4 w-4" aria-hidden="true" />
            重新识别当前视频
          </button>
        </div>

        <section class="border border-white/10 bg-[#0a0d12]">
          <div class="flex h-9 items-center justify-between border-b border-white/10 px-3">
            <h3 class="text-xs font-semibold text-[#cbd5e1]">后台任务</h3>
            <span class="text-[11px] text-[#7d8998]">{{ formatCount(analysisJobs.length) }} 条</span>
          </div>
          <div v-if="analysisJobs.length > 0" class="max-h-[360px] overflow-y-auto">
            <div
              v-for="job in analysisJobs"
              :key="job.job_id"
              class="border-b border-white/10 px-3 py-3 last:border-b-0"
              :class="job.job_id === activeAnalyzeJobId ? 'bg-[#111b20]' : ''"
            >
              <div class="flex items-center justify-between gap-2">
                <span class="truncate text-xs font-semibold text-[#f8fafc]">
                  {{ job.total > 1 ? `批量 ${formatCount(job.total)} 个视频` : compactPath(job.video_paths[0] || job.video_path || "") }}
                </span>
                <span
                  class="shrink-0 text-[11px] font-semibold"
                  :class="jobStatusClass(job.status)"
                >
                  {{ jobStatusLabel(job.status) }}
                </span>
              </div>
              <div class="mt-2 h-1 overflow-hidden bg-black/45">
                <div
                  class="h-full bg-[#34d5c8]"
                  :style="{ width: `${jobProgressPercent(job)}%` }"
                />
              </div>
              <div class="mt-2 flex items-center justify-between gap-2 text-[11px] text-[#7d8998]">
                <span class="truncate">{{ job.message }}</span>
                <span class="timecode shrink-0">{{ formatCount(jobProgressPercent(job)) }}%</span>
              </div>
              <div class="mt-2 grid grid-cols-3 border border-white/10 bg-[#05070a] text-[11px]">
                <span class="min-w-0 border-r border-white/10 px-2 py-1.5">
                  <span class="block text-[#536171]">分辨率</span>
                  <span class="mt-0.5 block truncate text-[#cbd5e1]">{{ jobResolutionLabel(job) }}</span>
                </span>
                <span class="min-w-0 border-r border-white/10 px-2 py-1.5">
                  <span class="block text-[#536171]">时长</span>
                  <span class="timecode mt-0.5 block text-[#cbd5e1]">{{ jobDurationLabel(job) }}</span>
                </span>
                <span class="min-w-0 px-2 py-1.5">
                  <span class="block text-[#536171]">耗时</span>
                  <span class="timecode mt-0.5 block text-[#34d5c8]">{{ jobElapsedLabel(job) }}</span>
                </span>
              </div>
              <div v-if="job.items.length > 1" class="mt-2 space-y-1">
                <div
                  v-for="item in job.items"
                  :key="item.video_path"
                  class="grid grid-cols-[minmax(0,1fr)_44px] gap-2 text-[11px]"
                >
                  <span class="truncate text-[#8f9bac]">{{ compactPath(item.video_path) }}</span>
                  <span class="text-right" :class="jobStatusClass(item.status)">
                    {{ jobStatusLabel(item.status) }}
                  </span>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="px-3 py-6 text-sm text-[#7d8998]">
            暂无后台任务。
          </div>
        </section>

        <form class="space-y-2" @submit.prevent="$emit('analyzePath')">
          <label class="block">
            <span class="mb-1 block text-[11px] font-semibold uppercase tracking-[0.16em] text-[#697586]">
              Video Path
            </span>
            <span class="flex border border-white/10 bg-[#0a0d12] focus-within:border-[#34d5c8]/70">
              <input
                :value="serverVideoPath"
                autocomplete="off"
                class="h-9 min-w-0 flex-1 bg-transparent px-3 text-sm text-[#eef2f7] placeholder:text-[#536171] focus-visible:outline-none"
                name="serverVideoPath"
                placeholder="data/a.mp4; data/b.mp4"
                :disabled="isBusy"
                @input="$emit('update:serverVideoPath', ($event.target as HTMLInputElement).value)"
              />
              <button
                class="grid h-9 w-10 shrink-0 place-items-center border-l border-white/10 text-[#34d5c8] transition-colors duration-150 hover:bg-[#12252a] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]"
                type="submit"
                :disabled="isBusy || serverVideoPath.trim().length === 0"
                aria-label="分析视频路径"
              >
                <Play class="h-4 w-4" aria-hidden="true" />
              </button>
            </span>
          </label>
        </form>

        <form class="space-y-2" @submit.prevent="$emit('importTimeline')">
          <label class="block">
            <span class="mb-1 block text-[11px] font-semibold uppercase tracking-[0.16em] text-[#697586]">
              Timeline JSON
            </span>
            <span class="flex border border-white/10 bg-[#0a0d12] focus-within:border-[#34d5c8]/70">
              <input
                :value="timelinePath"
                autocomplete="off"
                class="h-9 min-w-0 flex-1 bg-transparent px-3 text-sm text-[#eef2f7] placeholder:text-[#536171] focus-visible:outline-none"
                name="timelinePath"
                placeholder="_outputs/palace/timeline.json"
                :disabled="isBusy"
                @input="$emit('update:timelinePath', ($event.target as HTMLInputElement).value)"
              />
              <button
                class="grid h-9 w-10 shrink-0 place-items-center border-l border-white/10 text-[#f5c451] transition-colors duration-150 hover:bg-[#2a2414] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#f5c451]"
                type="submit"
                :disabled="isBusy || timelinePath.trim().length === 0"
                aria-label="导入时间轴"
              >
                <FolderInput class="h-4 w-4" aria-hidden="true" />
              </button>
            </span>
          </label>
        </form>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import {
  Cpu,
  Database,
  FileVideo,
  FolderInput,
  Loader2,
  Play,
  RotateCcw,
  Search,
  Settings2,
  Square,
  Trash2,
  Upload
} from "@lucide/vue";
import { computed, ref } from "vue";

import type { HardwareProfileId, HardwareProfileItem, HardwareSummary, VideoItem } from "../../api";
import type { AnalyzeJobStatus } from "../../api";
import { formatCount, formatTime } from "./workspaceUtils";

/** 媒体侧栏当前显示的标签页。 */
type SidebarTab = "library" | "import" | "trash";

/** 后端硬件探测失败时使用的默认配置列表。 */
const fallbackHardwareProfiles: HardwareProfileItem[] = [
  {
    id: "auto",
    label: "Auto",
    preferred_providers: [],
    note: "按当前 ONNX Runtime provider 自动选择。",
    available: true,
  },
  {
    id: "cpu",
    label: "CPU",
    preferred_providers: ["CPUExecutionProvider"],
    note: "最稳定，速度取决于 CPU。",
    available: true,
  },
  {
    id: "apple",
    label: "Apple CoreML",
    preferred_providers: ["CoreMLExecutionProvider"],
    note: "适合 Apple Silicon，需要 CoreMLExecutionProvider。",
    available: false,
  },
  {
    id: "nvidia",
    label: "NVIDIA CUDA",
    preferred_providers: ["CUDAExecutionProvider"],
    note: "适合 NVIDIA GPU，需要 CUDA 版 ONNX Runtime。",
    available: false,
  },
  {
    id: "intel",
    label: "Intel GPU",
    preferred_providers: ["OpenVINOExecutionProvider", "DmlExecutionProvider"],
    note: "适合 Intel Arc/A770，优先 OpenVINO，Windows 可用 DirectML。",
    available: false,
  },
];

/** 媒体侧栏接收的视频、导入和分析状态。 */
const props = defineProps<{
  videos: VideoItem[];
  trashVideos: VideoItem[];
  selectedVideoId: number | null;
  serverVideoPath: string;
  timelinePath: string;
  videoQuery: string;
  seriesName: string;
  configPath: string;
  isBusy: boolean;
  busyLabel: string;
  operationProgressPercent: number;
  operationProgressMessage: string;
  analysisElapsedLabel: string;
  useCache: boolean;
  expectedPeopleCount: number | null;
  hardwareSummary: HardwareSummary | null;
  hardwareProfile: HardwareProfileId;
  allowCpuFallback: boolean;
  canReanalyzeSelected: boolean;
  canCancelAnalysis: boolean;
  pendingImportCount: number;
  analysisJobs: AnalyzeJobStatus[];
  activeAnalyzeJobId: string | null;
}>();

/** 媒体侧栏向工作台提交导入、分析和素材管理动作。 */
const emit = defineEmits<{
  "update:serverVideoPath": [value: string];
  "update:timelinePath": [value: string];
  "update:videoQuery": [value: string];
  "update:seriesName": [value: string];
  "update:configPath": [value: string];
  "update:useCache": [value: boolean];
  "update:expectedPeopleCount": [value: number | null];
  "update:hardwareProfile": [value: HardwareProfileId];
  "update:allowCpuFallback": [value: boolean];
  uploadFiles: [files: File[]];
  analyzePath: [];
  importTimeline: [];
  reanalyzeSelected: [];
  cancelAnalysis: [];
  selectVideo: [videoId: number];
  trashVideo: [videoId: number];
  restoreVideo: [videoId: number];
  purgeVideo: [videoId: number];
}>();

/** 文件拖入区域是否处于悬停状态。 */
const isDragging = ref(false);
/** 隐藏文件输入框的 DOM 引用。 */
const fileInputEl = ref<HTMLInputElement | null>(null);
/** 当前侧栏标签页。 */
const activeSidebarTab = ref<SidebarTab>("library");
/** 当前可展示的硬件配置列表。 */
const hardwareProfiles = computed(() =>
  props.hardwareSummary?.profiles.length ? props.hardwareSummary.profiles : fallbackHardwareProfiles
);
/** 推荐硬件配置的展示标签。 */
const recommendedHardwareLabel = computed(() =>
  hardwareProfileLabel(props.hardwareSummary?.recommended_profile ?? "auto")
);
/** 当前硬件配置的说明文案。 */
const selectedHardwareNote = computed(() => {
  const selected = hardwareProfiles.value.find((profile) => profile.id === props.hardwareProfile);
  return selected?.note ?? "按配置文件中的 provider 设置执行。";
});
/** 可用 ONNX Runtime provider 的短标签。 */
const availableProviderLabel = computed(() =>
  formatProviders(props.hardwareSummary?.available_providers ?? [])
);
/** GPU 设备列表的展示标签。 */
const gpuDeviceLabel = computed(() => (props.hardwareSummary?.gpu_devices ?? []).join(" / "));
/** 按搜索词过滤后的视频列表。 */
const filteredVideos = computed(() => {
  const query = props.videoQuery.trim().toLowerCase();
  if (!query) return props.videos;
  return props.videos.filter((video) => {
    return (
      videoDisplayTitle(video).toLowerCase().includes(query) ||
      video.series_name.toLowerCase().includes(query) ||
      (video.original_filename ?? "").toLowerCase().includes(query) ||
      (video.source_path ?? "").toLowerCase().includes(query) ||
      video.source_directory.toLowerCase().includes(query) ||
      video.path.toLowerCase().includes(query)
    );
  });
});

/** 标记拖拽文件进入上传区域。 */
function handleDragEnter() {
  isDragging.value = true;
}

/** 标记拖拽文件悬停在上传区域。 */
function handleDragOver() {
  isDragging.value = true;
}

/** 鼠标离开整个上传区域后取消拖拽态。 */
function handleDragLeave(event: DragEvent) {
  const current = event.currentTarget as HTMLElement;
  if (!current.contains(event.relatedTarget as Node | null)) {
    isDragging.value = false;
  }
}

/** 处理拖放上传的视频文件。 */
function handleDrop(event: DragEvent) {
  isDragging.value = false;
  const files = Array.from(event.dataTransfer?.files ?? []);
  if (files.length > 0) emit("uploadFiles", files);
}

/** 处理文件选择器上传的视频文件。 */
function handleFileInput(event: Event) {
  const input = event.target as HTMLInputElement;
  const files = Array.from(input.files ?? []);
  if (files.length > 0) emit("uploadFiles", files);
  if (fileInputEl.value) fileInputEl.value.value = "";
}

/** 解析预期人物数量输入并同步给父级。 */
function handleExpectedPeopleCountInput(event: Event) {
  const input = event.target as HTMLInputElement;
  const raw = input.value.trim();
  if (!raw) {
    emit("update:expectedPeopleCount", null);
    return;
  }
  const parsed = Number(raw);
  emit("update:expectedPeopleCount", Number.isInteger(parsed) && parsed >= 1 ? parsed : null);
}

/** 同步硬件配置下拉选择。 */
function handleHardwareProfileInput(event: Event) {
  emit("update:hardwareProfile", (event.target as HTMLSelectElement).value as HardwareProfileId);
}

/** 同步是否允许 CPU fallback 的开关。 */
function handleCpuFallbackInput(event: Event) {
  emit("update:allowCpuFallback", (event.target as HTMLInputElement).checked);
}

/** 将分析任务进度转换为百分比。 */
function jobProgressPercent(job: AnalyzeJobStatus) {
  return Math.round(Math.min(Math.max(job.progress, 0), 1) * 100);
}

/** 将任务状态转换为中文标签。 */
function jobStatusLabel(status: AnalyzeJobStatus["status"]) {
  if (status === "queued") return "排队";
  if (status === "running") return "运行";
  if (status === "succeeded") return "完成";
  if (status === "failed") return "失败";
  if (status === "canceled") return "终止";
  return status;
}

/** 为任务状态选择对应的文字颜色类。 */
function jobStatusClass(status: AnalyzeJobStatus["status"]) {
  if (status === "succeeded") return "text-[#34d5c8]";
  if (status === "failed") return "text-[#fecaca]";
  if (status === "canceled") return "text-[#f5c451]";
  if (status === "running") return "text-[#74f2e8]";
  return "text-[#8f9bac]";
}

/** 找到分析任务关联的主要视频。 */
function jobPrimaryVideo(job: AnalyzeJobStatus) {
  const itemVideoIds = job.items.map((item) => item.video_id).filter((id): id is number => id !== null);
  const videoIds = [job.video_id, ...itemVideoIds].filter((id): id is number => id !== null);
  for (const videoId of videoIds) {
    const video = props.videos.find((item) => item.id === videoId);
    if (video) return video;
  }
  const paths = [job.video_path, ...job.video_paths].filter((path): path is string => Boolean(path));
  return props.videos.find((video) => paths.includes(video.path) || paths.includes(video.source_path ?? ""));
}

/** 生成任务关联视频的分辨率标签。 */
function jobResolutionLabel(job: AnalyzeJobStatus) {
  const video = jobPrimaryVideo(job);
  return video ? `${video.width} x ${video.height}` : "--";
}

/** 生成任务关联视频的总时长标签。 */
function jobDurationLabel(job: AnalyzeJobStatus) {
  const video = jobPrimaryVideo(job);
  return video ? formatTime(video.duration_seconds) : "--";
}

/** 生成任务已耗时标签。 */
function jobElapsedLabel(job: AnalyzeJobStatus) {
  const video = jobPrimaryVideo(job);
  if (video?.analysis_elapsed_seconds !== null && video?.analysis_elapsed_seconds !== undefined) {
    return formatTime(video.analysis_elapsed_seconds);
  }
  const startedAt = parseJobTimestamp(job.created_at);
  if (!startedAt) return "--";
  const finishedAt =
    job.status === "queued" || job.status === "running"
      ? Date.now()
      : parseJobTimestamp(job.updated_at) ?? Date.now();
  return formatTime(Math.max((finishedAt - startedAt) / 1000, 0));
}

/** 解析后端任务时间戳为毫秒时间。 */
function parseJobTimestamp(value: string | null) {
  if (!value) return null;
  const normalized = value.includes("T") ? value : `${value.replace(" ", "T")}Z`;
  const parsed = Date.parse(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

/** 获取硬件配置的展示名称。 */
function hardwareProfileLabel(profileId: HardwareProfileId) {
  return hardwareProfiles.value.find((profile) => profile.id === profileId)?.label ?? profileId;
}

/** 将 provider 列表格式化为短名称。 */
function formatProviders(providers: string[]) {
  if (providers.length === 0) return "未检测到";
  return providers.map(shortProviderName).join(" / ");
}

/** 移除 provider 名中的 ExecutionProvider 后缀。 */
function shortProviderName(provider: string) {
  return provider.replace("ExecutionProvider", "") || provider;
}

/** 优先用作品元数据生成视频标题。 */
function videoDisplayTitle(video: VideoItem) {
  const title = meaningfulTitle(video.title);
  if (title) return title;
  if (video.original_filename) return stripExtension(video.original_filename);
  if (video.source_path) return stripExtension(compactPath(video.source_path));
  return stripExtension(compactPath(video.path));
}

/** 生成视频来源路径的紧凑展示。 */
function videoSourceLine(video: VideoItem) {
  if (video.source_directory) return video.source_directory;
  if (video.source_path) return compactPath(video.source_path);
  return compactPath(video.path);
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

/** 将长路径压缩为末两级目录。 */
function compactPath(path: string) {
  const parts = path.split(/[\\/]/).filter(Boolean);
  if (parts.length <= 2) return path;
  return `${parts.at(-2)}/${parts.at(-1)}`;
}

</script>

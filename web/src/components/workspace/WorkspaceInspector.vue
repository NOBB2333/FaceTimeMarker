<template>
  <aside class="inspector-panel min-w-0 overflow-y-auto border-l border-white/10 bg-[#0f1319]">
    <section class="border-b border-white/10 p-4">
      <div class="flex items-start gap-3">
        <img
          v-if="selectedPerson?.representative_face_path"
          class="h-16 w-16 shrink-0 object-cover"
          :src="mediaUrl(selectedPerson.representative_face_path)"
          :alt="`${selectedPerson.label} 代表脸`"
          width="64"
          height="64"
          loading="lazy"
        />
        <span v-else class="grid h-16 w-16 shrink-0 place-items-center border border-white/10 bg-[#151b23] text-[#697586]">
          <User class="h-7 w-7" aria-hidden="true" />
        </span>
        <div class="min-w-0 flex-1">
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0">
              <h2 class="truncate text-base font-semibold text-[#f8fafc]">{{ selectedPersonLabel }}</h2>
              <p class="mt-1 truncate text-xs text-[#7d8998]">
                {{ selectedPerson?.global_person_id ?? "未关联人物档案" }}
              </p>
            </div>
            <button
              v-if="selectedPersonId !== null"
              class="grid h-8 w-8 shrink-0 place-items-center border border-white/10 bg-[#151b23] text-[#8f9bac] transition-colors duration-150 hover:border-[#34d5c8]/60 hover:text-[#34d5c8] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]"
              type="button"
              aria-label="取消人物选中"
              @click="$emit('selectPerson', null)"
            >
              <X class="h-4 w-4" aria-hidden="true" />
            </button>
            <Users v-else class="mt-1 h-4 w-4 shrink-0 text-[#34d5c8]" aria-hidden="true" />
          </div>
          <div class="mt-3 grid grid-cols-3 border border-white/10 bg-[#0a0d12]">
            <div class="px-2 py-2">
              <div class="text-[11px] text-[#697586]">人物</div>
              <div class="mt-1 text-sm font-semibold">{{ formatCount(visiblePeopleCount) }}</div>
            </div>
            <div class="border-l border-white/10 px-2 py-2">
              <div class="text-[11px] text-[#697586]">片段</div>
              <div class="mt-1 text-sm font-semibold">{{ formatCount(visibleSegmentsCount) }}</div>
            </div>
            <div class="border-l border-white/10 px-2 py-2">
              <div class="text-[11px] text-[#697586]">时长</div>
              <div class="timecode mt-1 text-sm font-semibold">
                {{ formatTime(selectedPerson?.total_duration ?? 0) }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section
      class="right-inspector-section border-b border-white/10 bg-[#0c1016] p-4"
      :class="rightPanelSectionClass('metadata')"
      :style="rightPanelStyle('metadata')"
    >
      <div class="flex items-center justify-between gap-3">
        <h2 class="text-sm font-semibold">作品信息</h2>
        <span class="truncate text-xs text-[#7d8998]">{{ selectedVideo?.series_name || "未设置系列" }}</span>
      </div>
      <div class="mt-3 space-y-3 pr-1" :class="rightPanelBodyClass('metadata')">
        <label class="block">
          <span class="mb-1 block text-xs text-[#7d8998]">视频标题</span>
          <input
            :value="videoTitleDraft"
            autocomplete="off"
            class="h-9 w-full border border-white/10 bg-[#0a0d12] px-3 text-sm text-[#eef2f7] placeholder:text-[#536171] focus-visible:border-[#34d5c8] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]/60"
            name="videoTitle"
            placeholder="原作视频名"
            :disabled="!selectedVideo"
            @input="$emit('update:videoTitleDraft', ($event.target as HTMLInputElement).value)"
          />
        </label>
        <label class="block">
          <span class="mb-1 block text-xs text-[#7d8998]">系列/作品</span>
          <input
            :value="videoSeriesDraft"
            autocomplete="off"
            class="h-9 w-full border border-white/10 bg-[#0a0d12] px-3 text-sm text-[#eef2f7] placeholder:text-[#536171] focus-visible:border-[#34d5c8] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]/60"
            name="videoSeries"
            placeholder="例如 第一季 / 某电影系列"
            :disabled="!selectedVideo"
            @input="$emit('update:videoSeriesDraft', ($event.target as HTMLInputElement).value)"
          />
        </label>
        <label class="block">
          <span class="mb-1 block text-xs text-[#7d8998]">源文件路径</span>
          <input
            :value="videoSourcePathDraft"
            autocomplete="off"
            class="h-9 w-full border border-white/10 bg-[#0a0d12] px-3 text-sm text-[#eef2f7] placeholder:text-[#536171] focus-visible:border-[#34d5c8] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]/60"
            name="videoSourcePath"
            placeholder="源媒体丢失时，在这里重新链接"
            :disabled="!selectedVideo"
            @input="$emit('update:videoSourcePathDraft', ($event.target as HTMLInputElement).value)"
          />
        </label>
        <div class="border border-white/10 bg-[#0a0d12] px-3 py-2">
          <div class="text-xs text-[#697586]">来源目录</div>
          <div class="mt-1 truncate text-xs text-[#cbd5e1]">
            {{ selectedVideo?.source_directory || sourceDirectoryFromPath(videoSourcePathDraft) || "未记录" }}
          </div>
        </div>
        <button
          class="inline-flex h-9 w-full items-center justify-center gap-2 bg-[#34d5c8] px-3 text-sm font-semibold text-[#061211] transition-colors duration-150 hover:bg-[#74f2e8] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]"
          type="button"
          :disabled="!selectedVideo || isReviewing"
          @click="$emit('submitVideoMetadata')"
        >
          <Check class="h-4 w-4" aria-hidden="true" />
          保存作品信息
        </button>
      </div>
    </section>

    <div
      class="panel-resize-handle"
      role="separator"
      aria-label="调整作品信息高度"
      aria-orientation="horizontal"
      tabindex="0"
      @keydown="handleRightPanelResizeKeydown('metadata', $event)"
      @pointerdown="startRightPanelResize('metadata', $event)"
    >
      <span class="panel-resize-grip" aria-hidden="true" />
    </div>

    <section class="border-b border-white/10 p-4">
      <div class="flex items-center justify-between gap-3">
        <div class="flex items-center gap-2">
          <Users class="h-4 w-4 text-[#34d5c8]" aria-hidden="true" />
          <h2 class="text-sm font-semibold">全部人物</h2>
        </div>
        <span class="text-xs text-[#7d8998]">
          {{ formatCount(visiblePeopleCount) }} 人 / 隐藏 {{ formatCount(hiddenPeopleCount) }}
        </span>
      </div>
      <label class="mt-3 flex h-9 items-center gap-2 border border-white/10 bg-[#0a0d12] px-3">
        <Search class="h-4 w-4 text-[#697586]" aria-hidden="true" />
        <input
          :value="personQuery"
          autocomplete="off"
          name="personQuery"
          class="min-w-0 flex-1 bg-transparent text-sm text-[#eef2f7] placeholder:text-[#536171] focus-visible:outline-none"
          placeholder="搜索人物 ID"
          @input="$emit('update:personQuery', ($event.target as HTMLInputElement).value)"
        />
      </label>
    </section>

    <section
      class="right-inspector-section overflow-y-auto border-b border-white/10"
      :style="rightPanelStyle('people')"
    >
      <button
        class="flex w-full items-center justify-between border-b border-white/10 px-4 py-3 text-left transition-colors duration-150 hover:bg-[#151c24] focus-visible:outline focus-visible:outline-2 focus-visible:outline-inset focus-visible:outline-[#34d5c8]"
        :class="selectedPersonId === null ? 'bg-[#16232a]' : ''"
        type="button"
        @click="$emit('selectPerson', null)"
      >
        <span>
          <span class="block text-sm font-semibold">全部人物</span>
          <span class="text-xs text-[#7d8998]">{{ formatCount(segmentsCount) }} 个出现片段</span>
        </span>
        <List class="h-4 w-4 text-[#7d8998]" aria-hidden="true" />
      </button>

      <div
        v-for="person in filteredPeople"
        :key="person.id"
        class="grid w-full grid-cols-[minmax(0,1fr)_34px] gap-2 border-b border-white/10 px-4 py-3 text-left transition-colors duration-150 hover:bg-[#151c24]"
        :class="[
          selectedPersonId === person.person_id ? 'bg-[#16232a]' : '',
          personDropTargetId === person.person_id ? 'bg-[#1a2c25] shadow-[inset_3px_0_0_#34d5c8]' : '',
          isHiddenPerson(person) ? 'opacity-55' : ''
        ]"
        :data-person-drop-id="person.person_id"
        @dragenter.prevent="$emit('timelineSegmentDragOver', person.person_id)"
        @dragover.prevent="$emit('timelineSegmentDragOver', person.person_id)"
        @drop.prevent="$emit('dropTimelineSegmentOnPerson', draggedTimelineSegment, person.person_id)"
      >
        <button
          class="flex min-w-0 gap-3 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-inset focus-visible:outline-[#34d5c8]"
          type="button"
          @click="$emit('togglePersonSelection', person.person_id)"
        >
          <img
            v-if="person.representative_face_path"
            class="h-12 w-12 shrink-0 object-cover"
            :src="mediaUrl(person.representative_face_path)"
            :alt="`${person.label} 代表脸`"
            width="48"
            height="48"
            loading="lazy"
          />
          <span v-else class="grid h-12 w-12 shrink-0 place-items-center bg-[#151b23] text-[#697586]">
            <Image class="h-5 w-5" aria-hidden="true" />
          </span>
          <span class="min-w-0 flex-1">
            <span class="flex items-center justify-between gap-2">
              <span class="truncate text-sm font-semibold text-[#f8fafc]">
                {{ person.label }}{{ isHiddenPerson(person) ? " / 已隐藏" : "" }}
              </span>
              <span class="timecode shrink-0 text-xs text-[#34d5c8]">
                {{ formatCount(person.appearances) }} 段
              </span>
            </span>
            <span class="mt-1 block truncate text-xs text-[#7d8998]">
              {{ person.global_person_id ?? "未关联人物档案" }}
            </span>
            <span class="timecode mt-2 block text-xs text-[#cbd5e1]">
              {{ formatTime(person.total_duration) }} / {{ formatCount(person.detection_count) }} 检测
            </span>
          </span>
        </button>
        <button
          class="mt-0.5 grid h-8 w-8 place-items-center border border-white/10 bg-[#151b23] text-[#8f9bac] transition-colors duration-150 hover:border-[#f87171]/60 hover:text-[#fecaca] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#f87171]"
          type="button"
          :aria-label="`删除 ${person.label}`"
          title="删除人物"
          @click="$emit('confirmDeletePerson', person.person_id)"
        >
          <Trash2 class="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
    </section>

    <div
      class="panel-resize-handle"
      role="separator"
      aria-label="调整人物清单高度"
      aria-orientation="horizontal"
      tabindex="0"
      @keydown="handleRightPanelResizeKeydown('people', $event)"
      @pointerdown="startRightPanelResize('people', $event)"
    >
      <span class="panel-resize-grip" aria-hidden="true" />
    </div>

    <section
      class="right-inspector-section border-b border-white/10 bg-[#0c1016]"
      :class="rightPanelSectionClass('actions')"
      :style="rightPanelStyle('actions')"
    >
      <div class="flex h-11 items-center justify-between border-b border-white/10 px-4">
        <div class="flex items-center gap-2">
          <SlidersHorizontal class="h-4 w-4 text-[#f5c451]" aria-hidden="true" />
          <h2 class="text-sm font-semibold">快速操作</h2>
        </div>
        <span class="truncate text-xs text-[#7d8998]">{{ selectedPersonLabel }}</span>
      </div>

      <div class="space-y-3 px-4 py-4" :class="rightPanelBodyClass('actions')">
        <label class="block">
          <span class="mb-1 block text-xs text-[#7d8998]">显示名称</span>
          <input
            :value="reviewLabel"
            autocomplete="off"
            name="reviewLabel"
            class="h-9 w-full border border-white/10 bg-[#0a0d12] px-3 text-sm text-[#eef2f7] placeholder:text-[#536171] focus-visible:border-[#34d5c8] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]/60"
            placeholder="例如 男主角"
            :disabled="selectedPersonId === null"
            @input="$emit('update:reviewLabel', ($event.target as HTMLInputElement).value)"
          />
        </label>
        <div class="grid grid-cols-3 gap-2">
          <button
            class="inline-flex h-9 items-center justify-center gap-2 bg-[#f5c451] px-3 text-sm font-semibold text-[#11151b] transition-colors duration-150 hover:bg-[#ffd878] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#f5c451]"
            type="button"
            :disabled="selectedPersonId === null || isReviewing"
            @click="$emit('submitRename')"
          >
            <Check class="h-4 w-4" aria-hidden="true" />
            命名
          </button>
          <button
            class="inline-flex h-9 items-center justify-center gap-2 border border-white/10 bg-[#151b23] px-3 text-sm font-semibold text-[#cbd5e1] transition-colors duration-150 hover:border-[#34d5c8]/60 hover:text-[#34d5c8] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]"
            type="button"
            :disabled="selectedPersonId === null || isReviewing"
            @click="$emit('submitTogglePersonHidden')"
          >
            <Eye v-if="selectedPerson?.hidden" class="h-4 w-4" aria-hidden="true" />
            <EyeOff v-else class="h-4 w-4" aria-hidden="true" />
            {{ selectedPerson?.hidden ? "显示" : "隐藏" }}
          </button>
          <button
            class="inline-flex h-9 items-center justify-center gap-2 border border-[#7f2e2e] bg-[#2a1215] px-3 text-sm font-semibold text-[#fecaca] transition-colors duration-150 hover:bg-[#35171b] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#f87171]"
            type="button"
            :disabled="selectedPersonId === null || isReviewing"
            @click="$emit('submitDelete')"
          >
            <Trash2 class="h-4 w-4" aria-hidden="true" />
            删除
          </button>
        </div>
        <div class="border border-white/10 bg-[#0a0d12] p-3 text-xs leading-5 text-[#8f9bac]">
          大批量归类在中间的「批量整理人脸」面板完成；右侧保留命名、隐藏和删除误检。
        </div>
      </div>
    </section>

    <div
      class="panel-resize-handle"
      role="separator"
      aria-label="调整快速操作高度"
      aria-orientation="horizontal"
      tabindex="0"
      @keydown="handleRightPanelResizeKeydown('actions', $event)"
      @pointerdown="startRightPanelResize('actions', $event)"
    >
      <span class="panel-resize-grip" aria-hidden="true" />
    </div>

    <section
      class="right-inspector-section border-b border-white/10 bg-[#0c1016]"
      :class="rightPanelSectionClass('profile')"
      :style="rightPanelStyle('profile')"
    >
      <div class="flex h-11 items-center justify-between border-b border-white/10 px-4">
        <div class="flex items-center gap-2">
          <Network class="h-4 w-4 text-[#34d5c8]" aria-hidden="true" />
          <h2 class="text-sm font-semibold">人物档案</h2>
        </div>
        <span class="text-xs text-[#7d8998]">{{ formatCount(globalPeople.length) }} 组</span>
      </div>

      <div class="space-y-3 px-4 py-4" :class="rightPanelBodyClass('profile')">
        <div class="border border-white/10 bg-[#0a0d12] px-3 py-3">
          <div class="truncate text-xs text-[#7d8998]">当前关联</div>
          <div class="mt-1 truncate text-sm font-semibold text-[#f8fafc]">
            {{ selectedPerson?.global_person_id ?? "未关联人物档案" }}
          </div>
          <div class="mt-2 text-xs text-[#7d8998]">
            已确认 {{ formatCount(selectedGlobalPerson?.confirmed_count ?? 0) }} /
            {{ formatCount(selectedGlobalPerson?.observation_count ?? 0) }} 个观测
          </div>
        </div>
        <label class="block">
          <span class="mb-1 block text-xs text-[#7d8998]">关联到已有档案</span>
          <select
            :value="globalPersonTargetId"
            class="h-10 w-full border border-white/10 bg-[#0a0d12] px-3 text-sm text-[#eef2f7] focus-visible:border-[#34d5c8] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]/60"
            :disabled="selectedPersonId === null || globalPeople.length === 0"
            @change="$emit('update:globalPersonTargetId', ($event.target as HTMLSelectElement).value)"
          >
            <option value="">选择人物档案</option>
            <option
              v-for="person in globalPeople"
              :key="person.global_person_id"
              :value="person.global_person_id"
            >
              {{ globalPersonLabel(person) }}
            </option>
          </select>
          <p v-if="globalPeople.length === 0" class="mt-1 text-[11px] text-[#7d8998]">
            档案库为空，可以直接用下方按钮新建并关联当前人物。
          </p>
        </label>
        <button
          class="inline-flex h-9 w-full items-center justify-center gap-2 border border-[#34d5c8]/40 bg-[#112226] px-3 text-sm font-semibold text-[#74f2e8] transition-colors duration-150 hover:bg-[#173039] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]"
          type="button"
          :disabled="!canLinkGlobal || isGlobalReviewing"
          @click="$emit('submitLinkGlobal')"
        >
          <Check class="h-4 w-4" aria-hidden="true" />
          关联档案
        </button>
        <label class="block">
          <span class="mb-1 block text-xs text-[#7d8998]">新建人物档案</span>
          <input
            :value="newGlobalPersonLabel"
            autocomplete="off"
            class="h-9 w-full border border-white/10 bg-[#0a0d12] px-3 text-sm text-[#eef2f7] placeholder:text-[#536171] focus-visible:border-[#34d5c8] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]/60"
            name="newGlobalPersonLabel"
            placeholder="默认使用当前人物名称"
            :disabled="selectedPersonId === null || isGlobalReviewing"
            @input="$emit('update:newGlobalPersonLabel', ($event.target as HTMLInputElement).value)"
          />
        </label>
        <button
          class="inline-flex h-9 w-full items-center justify-center gap-2 border border-white/10 bg-[#151b23] px-3 text-sm font-semibold text-[#cbd5e1] transition-colors duration-150 hover:border-[#34d5c8]/60 hover:text-[#34d5c8] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]"
          type="button"
          :disabled="selectedPersonId === null || isGlobalReviewing"
          @click="$emit('submitCreateGlobalPerson')"
        >
          <Users class="h-4 w-4" aria-hidden="true" />
          新建并关联
        </button>
        <div class="grid grid-cols-2 gap-2">
          <button
            class="inline-flex h-9 items-center justify-center gap-2 bg-[#34d5c8] px-3 text-sm font-semibold text-[#061211] transition-colors duration-150 hover:bg-[#74f2e8] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]"
            type="button"
            :disabled="!canReviewGlobal || isGlobalReviewing"
            @click="$emit('submitConfirmGlobal')"
          >
            <Check class="h-4 w-4" aria-hidden="true" />
            确认匹配
          </button>
          <button
            class="inline-flex h-9 items-center justify-center gap-2 border border-[#7f2e2e] bg-[#2a1215] px-3 text-sm font-semibold text-[#fecaca] transition-colors duration-150 hover:bg-[#35171b] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#f87171]"
            type="button"
            :disabled="!canReviewGlobal || isGlobalReviewing"
            @click="$emit('submitRejectGlobal')"
          >
            <X class="h-4 w-4" aria-hidden="true" />
            拆成新档案
          </button>
        </div>
      </div>
    </section>

    <div
      class="panel-resize-handle"
      role="separator"
      aria-label="调整人物档案高度"
      aria-orientation="horizontal"
      tabindex="0"
      @keydown="handleRightPanelResizeKeydown('profile', $event)"
      @pointerdown="startRightPanelResize('profile', $event)"
    >
      <span class="panel-resize-grip" aria-hidden="true" />
    </div>

    <section
      class="right-inspector-section bg-[#0c1016]"
      :class="rightPanelSectionClass('segments')"
      :style="rightPanelStyle('segments')"
    >
      <div class="flex h-11 items-center justify-between border-b border-white/10 px-4">
        <div class="flex items-center gap-2">
          <Clock class="h-4 w-4 text-[#34d5c8]" aria-hidden="true" />
          <h2 class="text-sm font-semibold">出现片段</h2>
        </div>
        <span class="truncate text-xs text-[#7d8998]">{{ selectedPersonLabel }}</span>
      </div>

      <div :class="rightPanelBodyClass('segments')">
        <div
          v-for="segment in visibleSegments"
          :key="segment.id"
          class="grid grid-cols-[minmax(0,1fr)_36px] gap-2 border-b border-white/10 px-4 py-3"
          :class="activeSegmentId === segment.id ? 'bg-[#231d10]' : ''"
        >
          <button
            class="min-w-0 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#f5c451]"
            type="button"
            @click="$emit('jumpToSegment', segment)"
          >
            <span class="timecode block text-sm font-semibold text-[#f8fafc]">
              {{ formatTime(segment.start) }} - {{ formatTime(segment.end) }}
            </span>
            <span class="mt-1 block truncate text-xs text-[#7d8998]">
              {{ personName(segment.person_id) }} / {{ formatCount(segment.detection_count) }} 次检测
            </span>
          </button>
          <button
            :aria-label="`从 ${formatTime(segment.start)} 播放`"
            class="grid h-9 w-9 place-items-center border border-white/10 bg-[#151b23] text-[#f5c451] transition-colors duration-150 hover:border-[#f5c451]/60 hover:bg-[#2a2414] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#f5c451]"
            type="button"
            @click="$emit('playSegment', segment)"
          >
            <Play class="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        <div v-if="visibleSegments.length === 0" class="px-4 py-8 text-sm text-[#7d8998]">
          当前筛选下没有出现片段。
        </div>
      </div>
    </section>

    <div
      class="panel-resize-handle panel-resize-handle--end"
      role="separator"
      aria-label="调整出现片段高度"
      aria-orientation="horizontal"
      tabindex="0"
      @keydown="handleRightPanelResizeKeydown('segments', $event)"
      @pointerdown="startRightPanelResize('segments', $event)"
    >
      <span class="panel-resize-grip" aria-hidden="true" />
    </div>
  </aside>
</template>

<script setup lang="ts">
import {
  Check,
  Clock,
  Eye,
  EyeOff,
  Image,
  List,
  Network,
  Play,
  Search,
  SlidersHorizontal,
  Trash2,
  User,
  Users,
  X,
} from "@lucide/vue";
import type { StyleValue } from "vue";

import { mediaUrl, type GlobalPersonItem, type PersonItem, type SegmentItem, type VideoDetail } from "../../api";
import type { RightResizablePanelId } from "../../composables/useWorkspacePanelResize";

/** 工作台右侧详情栏的完整展示状态；数据加载和业务动作都由 WorkspacePage 管理。 */
defineProps<{
  selectedPerson: PersonItem | null;
  selectedPersonId: number | null;
  selectedPersonLabel: string;
  visiblePeopleCount: number;
  visibleSegmentsCount: number;
  hiddenPeopleCount: number;
  selectedVideo: VideoDetail | null;
  videoTitleDraft: string;
  videoSeriesDraft: string;
  videoSourcePathDraft: string;
  personQuery: string;
  filteredPeople: PersonItem[];
  segmentsCount: number;
  visibleSegments: SegmentItem[];
  activeSegmentId: number | null;
  personDropTargetId: number | null;
  draggedTimelineSegment: SegmentItem | null;
  reviewLabel: string;
  globalPersonTargetId: string;
  newGlobalPersonLabel: string;
  selectedGlobalPerson: GlobalPersonItem | null;
  globalPeople: GlobalPersonItem[];
  canLinkGlobal: boolean;
  canReviewGlobal: boolean;
  isReviewing: boolean;
  isGlobalReviewing: boolean;
  rightPanelStyle: (panelId: RightResizablePanelId) => StyleValue;
  rightPanelSectionClass: (panelId: RightResizablePanelId) => string;
  rightPanelBodyClass: (panelId: RightResizablePanelId) => string;
  startRightPanelResize: (panelId: RightResizablePanelId, event: PointerEvent) => void;
  handleRightPanelResizeKeydown: (panelId: RightResizablePanelId, event: KeyboardEvent) => void;
  formatCount: (value: number) => string;
  formatTime: (seconds: number) => string;
  sourceDirectoryFromPath: (path: string) => string;
  globalPersonLabel: (person: GlobalPersonItem) => string;
  personName: (personId: number) => string;
  isHiddenPerson: (person: { hidden?: number | boolean | null }) => boolean;
}>();

/** 右侧详情栏只上抛表单更新、人物选择和审阅动作，避免组件内直接调用 API。 */
defineEmits<{
  "update:videoTitleDraft": [value: string];
  "update:videoSeriesDraft": [value: string];
  "update:videoSourcePathDraft": [value: string];
  "update:personQuery": [value: string];
  "update:reviewLabel": [value: string];
  "update:globalPersonTargetId": [value: string];
  "update:newGlobalPersonLabel": [value: string];
  selectPerson: [personId: number | null];
  togglePersonSelection: [personId: number];
  confirmDeletePerson: [personId: number];
  timelineSegmentDragOver: [personId: number];
  dropTimelineSegmentOnPerson: [segment: SegmentItem | null, personId: number];
  submitVideoMetadata: [];
  submitRename: [];
  submitTogglePersonHidden: [];
  submitDelete: [];
  submitLinkGlobal: [];
  submitCreateGlobalPerson: [];
  submitConfirmGlobal: [];
  submitRejectGlobal: [];
  jumpToSegment: [segment: SegmentItem];
  playSegment: [segment: SegmentItem];
}>();
</script>

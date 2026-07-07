<template>
  <section class="border-b border-white/10 px-4 py-3">
    <div class="flex items-center justify-between gap-3">
      <h3 class="text-sm font-semibold text-[#f8fafc]">档案管理</h3>
      <span class="text-xs text-[#7d8998]">危险操作</span>
    </div>
    <label class="mt-3 block">
      <span class="mb-1 block text-xs text-[#7d8998]">档案名称</span>
      <input
        :value="profileLabel"
        autocomplete="off"
        class="h-9 w-full border border-white/10 bg-[#090d12] px-3 text-xs text-[#eef2f7] placeholder:text-[#536171] focus-visible:border-[#34d5c8] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]/60"
        name="profileLabel"
        placeholder="人物名称"
        :disabled="!selectedProfile || isRenaming"
        @input="emit('update:profileLabel', ($event.target as HTMLInputElement).value)"
      />
    </label>
    <button
      class="mt-2 inline-flex h-9 w-full items-center justify-center gap-2 border border-white/10 bg-[#151b23] px-3 text-xs font-semibold text-[#cbd5e1] transition-colors duration-150 hover:border-[#34d5c8]/60 hover:text-[#34d5c8] disabled:opacity-45 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]"
      type="button"
      :disabled="!canRename"
      @click="emit('rename')"
    >
      保存档案名称
    </button>
    <label class="mt-3 block">
      <span class="mb-1 block text-xs text-[#7d8998]">把其他档案合并到当前档案</span>
      <select
        :value="mergeSourceId"
        class="h-9 w-full border border-white/10 bg-[#090d12] px-3 text-xs text-[#eef2f7] focus-visible:border-[#34d5c8] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]/60"
        :disabled="mergeSourceProfiles.length === 0 || isMerging"
        @change="emit('update:mergeSourceId', ($event.target as HTMLSelectElement).value)"
      >
        <option value="">选择要合并进来的档案</option>
        <option
          v-for="person in mergeSourceProfiles"
          :key="person.global_person_id"
          :value="person.global_person_id"
        >
          {{ profileName(person) }} / {{ person.global_person_id }}
        </option>
      </select>
    </label>
    <button
      class="mt-2 inline-flex h-9 w-full items-center justify-center gap-2 border border-[#34d5c8]/45 bg-[#102322] px-3 text-xs font-semibold text-[#9ff4ec] transition-colors duration-150 hover:bg-[#15302e] disabled:opacity-45 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]"
      type="button"
      :disabled="!canMerge"
      @click="emit('merge')"
    >
      <GitMerge class="h-4 w-4" aria-hidden="true" />
      合并到当前档案
    </button>
    <button
      class="mt-2 inline-flex h-9 w-full items-center justify-center gap-2 border border-[#7f2e2e] bg-[#2a1215] px-3 text-xs font-semibold text-[#fecaca] transition-colors duration-150 hover:bg-[#35171b] disabled:opacity-45 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#f87171]"
      type="button"
      :disabled="!selectedProfile || isDeleting"
      @click="emit('delete')"
    >
      <Trash2 class="h-4 w-4" aria-hidden="true" />
      移入回收站
    </button>
    <div class="mt-4 border-t border-white/10 pt-3">
      <div class="flex items-center justify-between gap-3">
        <h4 class="text-xs font-semibold text-[#cbd5e1]">最近操作</h4>
        <span class="text-[11px] text-[#697586]">{{ formatCount(profileActions.length) }} 条</span>
      </div>
      <div v-if="profileActions.length > 0" class="mt-2 space-y-2">
        <div
          v-for="action in profileActions.slice(0, 6)"
          :key="action.id"
          class="border border-white/10 bg-[#090d12] px-3 py-2"
        >
          <div class="flex items-center justify-between gap-3">
            <span class="text-xs font-semibold text-[#f8fafc]">{{ profileActionLabel(action.action) }}</span>
            <span class="timecode text-[11px] text-[#7d8998]">{{ formatDateTime(action.created_at) }}</span>
          </div>
          <p v-if="profileActionSummary(action)" class="mt-1 truncate text-[11px] text-[#8f9bac]">
            {{ profileActionSummary(action) }}
          </p>
        </div>
      </div>
      <p v-else class="mt-2 text-xs text-[#697586]">暂无操作记录。</p>
    </div>
  </section>

  <section>
    <div class="border-b border-white/10 px-4 py-3">
      <h3 class="text-sm font-semibold text-[#f8fafc]">档案字段</h3>
    </div>
    <dl class="grid gap-0 text-sm">
      <div class="border-b border-white/10 px-4 py-3">
        <dt class="text-xs text-[#697586]">主要标签</dt>
        <dd class="mt-1 text-[#f8fafc]">{{ selectedProfile ? profileName(selectedProfile) : "--" }}</dd>
      </div>
      <div class="border-b border-white/10 px-4 py-3">
        <dt class="text-xs text-[#697586]">档案 ID</dt>
        <dd class="timecode mt-1 break-all text-[#34d5c8]">
          {{ selectedProfile?.global_person_id || "--" }}
        </dd>
      </div>
      <div class="border-b border-white/10 px-4 py-3">
        <dt class="text-xs text-[#697586]">参考素材</dt>
        <dd class="mt-1 text-[#f8fafc]">{{ formatCount(referenceCount) }} 张</dd>
      </div>
    </dl>
  </section>
</template>

<script setup lang="ts">
import { GitMerge, Trash2 } from "@lucide/vue";

import type { GlobalPersonActionItem, GlobalPersonItem } from "../../api";

/** 档案详情页右侧管理区所需的当前档案、合并候选和异步状态。 */
defineProps<{
  selectedProfile: GlobalPersonItem | null;
  profileLabel: string;
  mergeSourceId: string;
  mergeSourceProfiles: GlobalPersonItem[];
  profileActions: GlobalPersonActionItem[];
  referenceCount: number;
  canRename: boolean;
  canMerge: boolean;
  isRenaming: boolean;
  isMerging: boolean;
  isDeleting: boolean;
}>();

/** 所有档案管理动作都交给父页面执行，组件本身只负责表单展示和事件上抛。 */
const emit = defineEmits<{
  "update:profileLabel": [value: string];
  "update:mergeSourceId": [value: string];
  rename: [];
  merge: [];
  delete: [];
}>();

const numberFormatter = new Intl.NumberFormat("zh-CN");

/** 后端记录的动作类型到前端展示文案的映射。 */
const profileActionLabels: Record<string, string> = {
  create_manual_profile: "手动新建",
  rename_profile: "重命名",
  trash_profile: "移入回收站",
  restore_profile: "恢复档案",
  purge_profile: "彻底删除",
  merge_profile: "合并档案",
};

/** 优先展示人工命名，未命名时用稳定的全局人物 ID。 */
function profileName(person: GlobalPersonItem) {
  return person.label?.trim() || person.global_person_id;
}

/** 未识别的新动作类型保留原始 action，方便排查后端新增行为。 */
function profileActionLabel(action: string) {
  return profileActionLabels[action] ?? action;
}

/** 将操作历史 payload 中最关键的字段压成一行摘要。 */
function profileActionSummary(action: GlobalPersonActionItem) {
  if (action.action === "rename_profile" && typeof action.payload.label === "string") {
    return `新名称：${action.payload.label}`;
  }
  if (action.action === "merge_profile" && typeof action.payload.source_global_person_id === "string") {
    return `来源档案：${action.payload.source_global_person_id}`;
  }
  if (action.action === "trash_profile" && typeof action.payload.deleted_at === "string") {
    return `移入时间：${formatDateTime(action.payload.deleted_at)}`;
  }
  return "";
}

/** 格式化档案管理面板中的数量。 */
function formatCount(value: number) {
  return numberFormatter.format(value);
}

/** 操作历史只显示月日和时间，避免侧栏里出现过长时间戳。 */
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

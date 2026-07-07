<template>
  <div class="grid min-h-full place-items-center px-5 py-20 text-center">
    <div>
      <div class="mx-auto grid h-16 w-16 place-items-center border border-white/10 bg-[#111821] text-[#536171]">
        <UserRound class="h-8 w-8" aria-hidden="true" />
      </div>
      <p class="mt-4 text-sm font-semibold text-[#cbd5e1]">{{ label }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { UserRound } from "@lucide/vue";

/** 档案页通用空状态，仅接收外部文案以适配不同浏览模式。 */
defineProps<{
  label: string;
}>();
</script>

<template>
  <nav class="app-nav flex h-12 items-center justify-between border-b border-white/10 bg-[#11151b]/95 px-4">
    <div class="flex min-w-0 items-center gap-3">
      <span class="h-2.5 w-2.5 bg-[#34d5c8]" aria-hidden="true" />
      <span class="truncate text-sm font-semibold text-[#f8fafc]" translate="no">
        FaceTimeMarker
      </span>
    </div>
    <div class="flex items-center border border-white/10 bg-[#0d1117] p-1">
      <RouterLink
        v-for="page in pages"
        :key="page.id"
        v-slot="{ href, navigate, isActive }"
        :to="page.path"
        custom
      >
        <a
          :href="href"
        class="h-8 px-3 text-xs font-semibold text-[#8f9bac] transition-colors duration-150 hover:text-[#f8fafc] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#34d5c8]"
          :class="isActive ? 'bg-[#22313a] text-[#34d5c8]' : ''"
          :title="page.description"
          @click="navigate"
        >
          {{ page.label }}
        </a>
      </RouterLink>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { RouterLink } from "vue-router";

import type { AppPage } from "../app/pages";

/** 顶部导航接收的当前页和页面列表。 */
defineProps<{
  pages: AppPage[];
}>();
</script>

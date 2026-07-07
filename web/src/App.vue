<template>
  <main class="app-shell min-h-screen overflow-hidden bg-[#090b0f] text-[#eef2f7]">
    <AppNav :pages="appPages" />

    <RouterView class="h-[calc(100vh-48px)]" />
  </main>
</template>

<script setup lang="ts">
/** 应用根组件只承载全局导航和路由出口，页面状态由各路由组件维护。 */
import { RouterView } from "vue-router";

import { appPages } from "./app/pages";
import AppNav from "./components/AppNav.vue";
</script>

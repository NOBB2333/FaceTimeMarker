import { createRouter, createWebHistory } from "vue-router";

import { appPages } from "./app/pages";

/** 应用级路由。刷新页面时保留当前工作区，而不是回到默认页。 */
export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      redirect: "/workspace",
    },
    ...appPages.map((page) => ({
      path: page.path,
      name: page.id,
      component: page.component,
      meta: {
        label: page.label,
        description: page.description,
      },
    })),
    {
      path: "/:pathMatch(.*)*",
      redirect: "/workspace",
    },
  ],
});

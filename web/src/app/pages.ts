import type { Component } from "vue";

import ProfilesPage from "../pages/ProfilesPage.vue";
import SearchPage from "../pages/SearchPage.vue";
import WorkspacePage from "../pages/WorkspacePage.vue";

/** 顶部导航可切换的页面标识。 */
export type PageId = "workspace" | "profiles" | "search";

/** 顶部导航和动态组件渲染共用的页面配置。 */
export type AppPage = {
  id: PageId;
  path: string;
  label: string;
  description: string;
  component: Component;
};

/** 应用主导航的页面顺序和组件映射。 */
export const appPages: AppPage[] = [
  {
    id: "workspace",
    path: "/workspace",
    label: "工作台",
    description: "视频分析、人物时间轴和批量整理",
    component: WorkspacePage
  },
  {
    id: "profiles",
    path: "/profiles",
    label: "人物档案",
    description: "跨作品人物形象、观测和参考资产",
    component: ProfilesPage
  },
  {
    id: "search",
    path: "/search",
    label: "搜索",
    description: "按备注、视频和人脸图片检索人物库",
    component: SearchPage
  }
];

import { createApp } from "vue";
import App from "./App.vue";
import { router } from "./router";
import "./style.css";

/** 挂载前端 Vue 应用。 */
createApp(App).use(router).mount("#app");

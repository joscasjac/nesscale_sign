import { createApp } from "vue";
import "./style.css";
import { loadTranslations, translationPlugin } from "./translation.js";

// Load translations before importing the app so module-level __() calls see them.
loadTranslations().finally(async () => {
	const { default: App } = await import("./App.vue");
	createApp(App).use(translationPlugin).mount("#app");
});

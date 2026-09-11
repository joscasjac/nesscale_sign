import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
export default defineConfig({
	plugins: [vue()],
	base: process.env.LOCAL_PREVIEW ? "/" : "/assets/nesscale_sign/frontend/",
	build: { outDir: "../nesscale_sign/public/frontend", emptyOutDir: true },
	server: { proxy: { "/api": "http://127.0.0.1:4174", "/demo": "http://127.0.0.1:4174" } },
});

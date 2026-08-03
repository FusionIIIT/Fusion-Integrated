import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Same-origin in dev so the auth cookie is sent without CORS gymnastics.
    proxy: { "/api": { target: "http://127.0.0.1:8002", changeOrigin: true } },
  },
  // "hidden": maps are written for symbolising a stack trace, but the bundle
  // carries no sourceMappingURL, so a browser never fetches the source.
  build: { outDir: "dist", sourcemap: "hidden" },
});

import path from "path";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// Single source of config for the whole project: the repo-root .env (one file to
// maintain on a server — never edit source). npm runs scripts from client/, so the
// repo root is one level up.
const rootDir = path.resolve(process.cwd(), "..");

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, rootDir, "");
  // Sub-path the app is served under (default "/"; e.g. "/sysadmin/" in prod).
  const base = env.APP_BASE_PATH || process.env.APP_BASE_PATH || "/";
  return {
    base,
    envDir: rootDir, // read VITE_* from the repo-root .env too
    plugins: [react()],
    server: {
      host: true, // reachable over the box's LAN/Tailscale IP
      // Same-origin dev proxy so the httpOnly auth cookie is always sent. In prod a
      // reverse proxy (nginx) serves the SPA and forwards <base>/api to Django.
      proxy: {
        "/api": {
          target: "http://localhost:8000",
          changeOrigin: true,
        },
      },
    },
  };
});

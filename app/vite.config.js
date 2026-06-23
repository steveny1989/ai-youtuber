import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  root: path.resolve("app"),
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 4173,
    proxy: {
      "/api": "http://127.0.0.1:8787",
      "/workspace": "http://127.0.0.1:8787",
    },
  },
  build: {
    outDir: path.resolve("dist/app"),
    emptyOutDir: true,
  },
});

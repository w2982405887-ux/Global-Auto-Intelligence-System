import vinext from "vinext";
import { defineConfig } from "vite";

// macOS Seatbelt blocks FSEvents, so Codex previews need polling for HMR.
const isCodexSeatbeltSandbox = process.env.CODEX_SANDBOX === "seatbelt";
// The proxy target is a deployment/local-run setting, not a repository path.
// Override it with VITE_DEV_API_PROXY_TARGET when the backend is on another
// host or port; keep the loopback default for the local Docker/Postgres setup.
const devApiProxyTarget =
  process.env.VITE_DEV_API_PROXY_TARGET ?? "http://127.0.0.1:8000";

export default defineConfig({
  server: {
    // Keep browser requests same-origin during local development.  This
    // avoids cross-port client blocking while preserving the backend's
    // existing /api/v1 and health endpoints.
    proxy: {
      "/api/v1": {
        target: devApiProxyTarget,
        changeOrigin: true,
        secure: false,
      },
      "/health": {
        target: devApiProxyTarget,
        changeOrigin: true,
        secure: false,
      },
    },
    ...(isCodexSeatbeltSandbox
      ? { watch: { useFsEvents: false, usePolling: true } }
      : {}),
  },
  plugins: [vinext()],
});

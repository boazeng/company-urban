import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// NOTE: vite-plugin-pwa (service worker) was removed. Its workbox navigation
// fallback served the SPA's index.html for /reports/* (report links landed on
// the dashboard) and pinned stale bundles behind a Cloudflare→CloudFront cache,
// which no amount of "autoUpdate"/self-destroy could reliably flush on clients.
// The dashboard reads live data and gained nothing from offline precaching, so
// the SW is gone entirely. A static, self-destroying public/sw.js stays at /sw.js
// so any browser still carrying an old SW unregisters it and clears its caches on
// the next update check — then nothing re-registers (index.html no longer injects
// registerSW). Re-introduce a PWA scoped to /app later if the mobile app needs it.
export default defineConfig({
  plugins: [
    react(),
  ],
  server: {
    port: 5180,
    open: true,
    // allow reading the parent obsi_comp vault (the real Structure/Schedule .md) during dev.
    // in production this is replaced by an API.
    fs: { allow: ['..'] },
  },
})

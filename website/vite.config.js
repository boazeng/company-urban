import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      injectRegister: 'auto',
      includeAssets: ['apple-touch-icon.png'],
      manifest: {
        name: 'company framework',
        short_name: 'Tasks',
        description: 'המטלות שלי — תצוגת נייד',
        lang: 'he',
        dir: 'rtl',
        // the installed app opens straight to the mobile screen, not the desktop dashboard.
        start_url: '/app',
        scope: '/',
        display: 'standalone',
        orientation: 'portrait',
        background_color: '#FAF9F5',
        theme_color: '#1F3A5F',
        icons: [
          { src: 'icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
    }),
  ],
  server: {
    port: 5180,
    open: true,
    // allow reading the parent obsi_comp vault (the real Structure/Schedule .md) during dev.
    // in production this is replaced by an API.
    fs: { allow: ['..'] },
  },
})

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5180,
    open: true,
    // allow reading the parent obsi_comp vault (the real Structure/Schedule .md) during dev.
    // in production this is replaced by an API.
    fs: { allow: ['..'] },
  },
})

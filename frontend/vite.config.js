import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  // Keep built assets resolvable when Vercel serves the SPA through a rewrite.
  base: './',
  server: {
    // Keep this aligned with launch_demo.bat/.ps1 and the README.
    port: 5173,
    host: true
  }
})

import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"
import { VitePWA } from "vite-plugin-pwa"

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg', 'icons.svg'],
      manifest: {
        name: 'MedTrack ERP',
        short_name: 'MedTrack',
        description: 'Multi-tenant Manufacturing ERP System',
        theme_color: '#2563eb',
        background_color: '#ffffff',
        display: 'standalone',
        scope: '/',
        start_url: '/',
        categories: ['productivity', 'manufacturing'],
        screenshots: [
          {
            src: '/screenshots/mobile.png',
            sizes: '540x720',
            form_factor: 'narrow'
          },
          {
            src: '/screenshots/desktop.png',
            sizes: '1280x720',
            form_factor: 'wide'
          }
        ]
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,svg,png,ico,json}'],
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/api\..*\/.*/i,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              networkTimeoutSeconds: 10,
              expiration: {
                maxEntries: 50,
                maxAgeSeconds: 86400 // 24 hours
              }
            }
          },
          {
            urlPattern: /^https:\/\/.*\.(?:png|jpg|jpeg|svg|gif)$/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'image-cache',
              expiration: {
                maxEntries: 100,
                maxAgeSeconds: 604800 // 7 days
              }
            }
          }
        ]
      },
      devOptions: {
        enabled: process.env.VITE_PWA === 'true',
        navigateFallback: 'index.html',
        suppressWarnings: true
      }
    })
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5000,
    allowedHosts: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path,
        secure: false,
        ws: true,
      }
    }
  }
})

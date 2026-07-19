import path from "path";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";
import { VitePWA } from "vite-plugin-pwa";
function resolveApiTarget(env) {
    var explicitTarget = env.VITE_API_TARGET || env.VITE_BACKEND_TARGET;
    if (explicitTarget) {
        return explicitTarget;
    }
    var apiUrl = env.VITE_API_URL || "/api/v1";
    if (/^https?:\/\//i.test(apiUrl)) {
        try {
            return new URL(apiUrl).origin;
        }
        catch (_a) {
            // Fall through to the default backend target below.
        }
    }
    return "http://127.0.0.1:8001";
}
export default defineConfig(function (_a) {
    var mode = _a.mode;
    var env = loadEnv(mode, process.cwd(), "");
    var apiTarget = resolveApiTarget(env);
    return {
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
                react: path.resolve(__dirname, "./node_modules/react"),
                "react-dom": path.resolve(__dirname, "./node_modules/react-dom"),
            },
            dedupe: ["react", "react-dom"],
        },
        server: {
            host: '0.0.0.0',
            port: 5000,
            allowedHosts: true,
            proxy: {
                '/api': {
                    target: apiTarget,
                    changeOrigin: true,
                    secure: false,
                    ws: true,
                },
                '/docs': {
                    target: apiTarget,
                    changeOrigin: true,
                    secure: false,
                },
                '/redoc': {
                    target: apiTarget,
                    changeOrigin: true,
                    secure: false,
                },
                '/openapi.json': {
                    target: apiTarget,
                    changeOrigin: true,
                    secure: false,
                },
                '/docs/oauth2-redirect': {
                    target: apiTarget,
                    changeOrigin: true,
                    secure: false,
                }
            }
        }
    };
});

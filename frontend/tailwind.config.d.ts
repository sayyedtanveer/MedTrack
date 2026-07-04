declare const config: {
    darkMode: ["class"];
    content: string[];
    prefix: string;
    theme: {
        container: {
            center: true;
            padding: string;
            screens: {
                "2xl": string;
            };
        };
        extend: {
            colors: {
                border: string;
                input: string;
                ring: string;
                background: string;
                foreground: string;
                primary: {
                    50: "#eff6ff";
                    100: "#dbeafe";
                    200: "#bfdbfe";
                    300: "#93c5fd";
                    400: "#60a5fa";
                    500: "#3b82f6";
                    600: "#2563eb";
                    700: "#1d4ed8";
                    800: "#1e40af";
                    900: "#1e3a8a";
                    950: "#172554";
                    DEFAULT: string;
                    foreground: string;
                };
                secondary: {
                    DEFAULT: string;
                    foreground: string;
                };
                destructive: {
                    DEFAULT: string;
                    foreground: string;
                };
                muted: {
                    DEFAULT: string;
                    foreground: string;
                };
                accent: {
                    DEFAULT: string;
                    foreground: string;
                };
                popover: {
                    DEFAULT: string;
                    foreground: string;
                };
                card: {
                    DEFAULT: string;
                    foreground: string;
                };
                success: {
                    readonly light: "#f0fdf4";
                    readonly border: "#86efac";
                    readonly text: "#166534";
                    readonly icon: "#22c55e";
                };
                warning: {
                    readonly light: "#fffbeb";
                    readonly border: "#fcd34d";
                    readonly text: "#92400e";
                    readonly icon: "#f59e0b";
                };
                error: {
                    readonly light: "#fef2f2";
                    readonly border: "#fca5a5";
                    readonly text: "#991b1b";
                    readonly icon: "#ef4444";
                };
                info: {
                    readonly light: "#eff6ff";
                    readonly border: "#93c5fd";
                    readonly text: "#1e40af";
                    readonly icon: "#3b82f6";
                };
                neutral: {
                    readonly 50: "#f8fafc";
                    readonly 100: "#f1f5f9";
                    readonly 200: "#e2e8f0";
                    readonly 300: "#cbd5e1";
                    readonly 400: "#94a3b8";
                    readonly 500: "#64748b";
                    readonly 600: "#475569";
                    readonly 700: "#334155";
                    readonly 800: "#1e293b";
                    readonly 900: "#0f172a";
                };
            };
            borderRadius: {
                lg: string;
                md: string;
                sm: string;
                none: "0";
                'token-sm': "4px";
                'token-md': "8px";
                'token-lg': "12px";
                xl: "16px";
                '2xl': "24px";
                full: "9999px";
            };
            fontFamily: {
                sans: ["Inter", "system-ui", "sans-serif"];
                mono: ["JetBrains Mono", "monospace"];
            };
            fontSize: {
                xs: "0.75rem";
                sm: "0.875rem";
                base: "1rem";
                lg: "1.125rem";
                xl: "1.25rem";
                '2xl': "1.5rem";
                '3xl': "1.875rem";
            };
            fontWeight: {
                normal: "400";
                medium: "500";
                semibold: "600";
                bold: "700";
            };
            lineHeight: {
                tight: "1.25";
                snug: "1.375";
                normal: "1.5";
                relaxed: "1.625";
            };
            letterSpacing: {
                tight: "-0.025em";
                normal: "0em";
                wide: "0.025em";
                wider: "0.05em";
                widest: "0.1em";
            };
            spacing: {
                0: "0px";
                1: "4px";
                2: "8px";
                3: "12px";
                4: "16px";
                5: "20px";
                6: "24px";
                8: "32px";
                10: "40px";
                12: "48px";
                16: "64px";
                20: "80px";
                24: "96px";
            };
            boxShadow: {
                sm: "0 1px 2px 0 rgb(0 0 0 / 0.05)";
                md: "0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)";
                lg: "0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)";
                xl: "0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)";
            };
            keyframes: {
                "accordion-down": {
                    from: {
                        height: string;
                    };
                    to: {
                        height: string;
                    };
                };
                "accordion-up": {
                    from: {
                        height: string;
                    };
                    to: {
                        height: string;
                    };
                };
            };
            animation: {
                "accordion-down": string;
                "accordion-up": string;
            };
        };
    };
    plugins: any[];
};
export default config;

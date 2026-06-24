/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: "#08090C",
        surface: "#08090C",
        "surface-low": "#0F111A",
        "surface-high": "#171926",
        "surface-highest": "#242838",
        "outline-variant": "#242838",
        primary: "#00E5FF",
        secondary: "#10B981",
        error: "#EF4444",
        "on-surface": "#F3F4F6",
        "on-surface-variant": "#9CA3AF",
        border: "#1F2937",
      },
      fontFamily: {
        headline: ["Space Grotesk", "sans-serif"],
        body: ["Inter", "sans-serif"],
        mono: ["Space Grotesk", "monospace"],
      },
      borderRadius: {
        lg: "8px",
        md: "6px",
        sm: "4px",
      },
    },
  },
  plugins: [],
}

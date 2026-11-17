/** @type {import('tailwindcss').Config} */
const v = (name) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: { DEFAULT: v("ink"), soft: v("ink-soft"), faint: v("ink-faint") },
        paper: { DEFAULT: v("paper"), panel: v("panel"), line: v("line") },
        amber: { DEFAULT: v("amber"), dark: v("amber-dark"), light: v("amber-light") },
        teal: { DEFAULT: v("teal"), dark: v("teal-dark"), light: v("teal-light") },
        clay: { DEFAULT: v("clay") },
        sidebar: { DEFAULT: v("sidebar"), fg: v("sidebar-fg") },
      },
      fontFamily: {
        display: ["'Fraunces'", "serif"],
        sans: ["'IBM Plex Sans'", "system-ui", "sans-serif"],
        mono: ["'IBM Plex Mono'", "monospace"],
      },
      borderRadius: { card: "8px" },
      boxShadow: { card: "0 1px 2px rgb(0 0 0 / 0.04), 0 4px 16px rgb(0 0 0 / 0.04)" },
    },
  },
  plugins: [],
};

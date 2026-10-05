/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        terminal: {
          bg: "#0B0F17",
          card: "#111827",
          border: "#1F2937",
          text: "#E5E7EB",
          muted: "#9CA3AF",
          accent: "#38BDF8",
          warning: "#F59E0B",
          danger: "#EF4444",
          success: "#10B981"
        }
      }
    },
  },
  plugins: [],
}

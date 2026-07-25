/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'brand-navy': '#1E1E2E',
        'brand-blue': '#1E3A8A',
        'brand-slate': '#3B82F6',
        'brand-light': '#93C5FD',
        'brand-bg': '#F1F5F9',
        'brand-card': '#FFFFFF',
        'brand-success': '#22C55E'
      }
    },
  },
  plugins: [],
}

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'legal-navy': '#1a365d',
        'legal-gold': '#c9a227',
        'legal-cream': '#faf8f5',
      }
    },
  },
  plugins: [],
}

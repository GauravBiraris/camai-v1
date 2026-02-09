/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./*.{js,ts,jsx,tsx}",        // <--- Scans root files like App.tsx
    "./components/**/*.{js,ts,jsx,tsx}", // <--- Scans components folder
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
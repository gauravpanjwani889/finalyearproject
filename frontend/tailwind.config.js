/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        grid: {
          950: '#070b12',
          900: '#0c1220',
          850: '#111a2e',
          800: '#16233b',
          700: '#213354',
          600: '#334e7d',
        },
        cyan: {
          400: '#22d3ee',
          500: '#06b6d4',
          glow: '#00f0ff',
        },
        amber: {
          400: '#fbbf24',
          500: '#f59e0b',
          glow: '#ffb703',
        },
        rose: {
          500: '#f43f5e',
          600: '#e11d48',
          glow: '#ff0055',
        },
        emerald: {
          400: '#34d399',
          500: '#10b981',
          glow: '#00ff88',
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

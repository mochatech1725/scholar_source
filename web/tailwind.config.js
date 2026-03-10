/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#2563eb', // Professional blue
          dark: '#1e40af',    // Darker blue
          light: '#3b82f6',   // Light blue
          '50': '#eff6ff',
          '100': '#dbeafe',
          '200': '#bfdbfe',
          '300': '#93c5fd',
          '400': '#60a5fa',
          '500': '#3b82f6',
          '600': '#2563eb',
          '700': '#1d4ed8',
          '800': '#1e40af',
          '900': '#1e3a8a',
        },
        // Slate Cobalt hero palette
        cobalt: {
          DEFAULT: '#2c5282',
          dark: '#1e3a5f',
          darker: '#1a3254',
        },
        accent: {
          DEFAULT: '#0ea5e9', // Sky blue
          dark: '#0284c7',    // Darker sky
          light: '#38bdf8',   // Light sky
        },
        success: '#22c55e',
      },
      fontFamily: {
        sans: ['Sora', 'system-ui', '-apple-system', 'sans-serif'],
        serif: ['Fraunces', 'Georgia', 'serif'],
        mono: ['DM Mono', 'monospace'],
      },
      spacing: {
        xs: '4px',
        sm: '8px',
        md: '16px',
        lg: '24px',
        xl: '32px',
        '2xl': '48px',
      },
      keyframes: {
        slideDown: {
          '0%': { opacity: '0', transform: 'translateY(-10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulse: {
          '0%, 100%': { transform: 'scale(1)', opacity: '0.3' },
          '50%': { transform: 'scale(1.1)', opacity: '0.5' },
        },
        pulseGreen: {
          '0%, 100%': { transform: 'scale(1)', opacity: '0.3' },
          '50%': { transform: 'scale(1.1)', opacity: '0.5' },
        },
      },
      animation: {
        slideDown: 'slideDown 0.2s ease-out',
        pulse: 'pulse 4s ease-in-out infinite',
        pulseGreen: 'pulseGreen 4s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}

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
          50: '#fff1f1',
          100: '#ffe4e4',
          200: '#ffcdcd',
          300: '#fda5a5',
          400: '#f87171',
          500: '#e63946',
          600: '#d62828',
          700: '#b71c1c',
          800: '#971515',
          900: '#7a1212',
          950: '#3e0707',
        },
        lava: {
          light: '#f87171',
          DEFAULT: '#e63946',
          dark: '#b71c1c',
          glow: '#fca5a5',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        'soft': '0 1px 3px 0 rgb(0 0 0 / 0.03), 0 1px 2px -1px rgb(0 0 0 / 0.06)',
        'card': '0 1px 4px 0 rgb(0 0 0 / 0.04), 0 2px 8px 0 rgb(0 0 0 / 0.02)',
        'card-hover': '0 4px 16px 0 rgb(0 0 0 / 0.06), 0 2px 8px 0 rgb(0 0 0 / 0.04)',
        'elevated': '0 8px 32px 0 rgb(0 0 0 / 0.08), 0 2px 8px 0 rgb(0 0 0 / 0.04)',
        'glow': '0 0 20px rgb(230 57 70 / 0.15), 0 4px 16px rgb(230 57 70 / 0.1)',
        'glow-lg': '0 0 32px rgb(230 57 70 / 0.2), 0 8px 24px rgb(230 57 70 / 0.12)',
        'soft-dark': '0 1px 3px 0 rgb(0 0 0 / 0.4), 0 1px 2px -1px rgb(0 0 0 / 0.5)',
        'card-dark': '0 1px 4px 0 rgb(0 0 0 / 0.5), 0 2px 8px 0 rgb(0 0 0 / 0.3)',
        'card-hover-dark': '0 4px 16px 0 rgb(0 0 0 / 0.6), 0 2px 8px 0 rgb(0 0 0 / 0.4)',
        'elevated-dark': '0 8px 32px 0 rgb(0 0 0 / 0.7), 0 2px 8px 0 rgb(0 0 0 / 0.4)',
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-out forwards',
        'fade-in-up': 'fadeInUp 0.5s ease-out forwards',
        'fade-in-down': 'fadeInDown 0.4s ease-out forwards',
        'scale-in': 'scaleIn 0.35s ease-out forwards',
        'slide-up': 'slideUp 0.5s ease-out forwards',
        'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
        'shimmer': 'shimmer 2s linear infinite',
        'float': 'float 3s ease-in-out infinite',
        'fluid': 'fluid 8s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        fadeInUp: {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        fadeInDown: {
          '0%': { opacity: '0', transform: 'translateY(-8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        scaleIn: {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 12px rgb(230 57 70 / 0.2)' },
          '50%': { boxShadow: '0 0 24px rgb(230 57 70 / 0.4)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-8px)' },
        },
        fluid: {
          '0%, 100%': { transform: 'translate(0, 0) scale(1)' },
          '25%': { transform: 'translate(5%, -3%) scale(1.02)' },
          '50%': { transform: 'translate(-3%, 5%) scale(0.98)' },
          '75%': { transform: 'translate(3%, -2%) scale(1.01)' },
        },
      },
      transitionDuration: {
        '250': '250ms',
        '400': '400ms',
      },
    },
  },
  plugins: [],
}

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary:  '#6366F1',   // indigo  — main actions, active nav
        accent:   '#8B5CF6',   // violet  — secondary highlights
        success:  '#22C55E',   // emerald — safe / present
        danger:   '#EF4444',   // red     — critical / absent
        warn:     '#F59E0B',   // amber   — warnings / late / teacher names
        info:     '#06B6D4',   // cyan    — info accents
        surface: {
          dark:    '#0F1117',  // sidebar, top bars
          DEFAULT: '#161B27',  // card / panel backgrounds
          light:   '#1E2538',  // elevated surfaces, hover states
        },
        background: '#080B12', // page background
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
      keyframes: {
        shimmer: {
          '100%': { transform: 'translateX(100%)' },
        },
        bounceIcon: {
          '0%, 100%': { transform: 'translateY(-10%)' },
          '50%': { transform: 'translateY(10%)' },
        },
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 10px rgba(99,102,241,0.4)' },
          '50%': { boxShadow: '0 0 32px rgba(99,102,241,0.85)' },
        },
        gradientShift: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
        fadeSlideUp: {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        float1: {
          '0%, 100%': { transform: 'translate(0px, 0px) scale(1)' },
          '33%':       { transform: 'translate(70px, -50px) scale(1.1)' },
          '66%':       { transform: 'translate(-40px, 35px) scale(0.95)' },
        },
        float2: {
          '0%, 100%': { transform: 'translate(0px, 0px) scale(1)' },
          '33%':       { transform: 'translate(-60px, 65px) scale(1.05)' },
          '66%':       { transform: 'translate(50px, -40px) scale(1.1)' },
        },
        float3: {
          '0%, 100%': { transform: 'translate(0px, 0px) scale(1)' },
          '50%':       { transform: 'translate(40px, -60px) scale(1.08)' },
        },
      },
      animation: {
        'bounce-icon':   'bounceIcon 2s ease-in-out infinite',
        'pulse-glow':    'pulseGlow 2.5s ease-in-out infinite',
        'gradient':      'gradientShift 10s ease infinite',
        'fade-slide-up': 'fadeSlideUp 0.3s ease-out',
        'float-1':       'float1 20s ease-in-out infinite',
        'float-2':       'float2 25s ease-in-out infinite',
        'float-3':       'float3 18s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}

module.exports = {
  content: ['./src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['DM Sans', 'sans-serif'],
        mono: ['DM Mono', 'monospace'],
      },
      colors: {
        app:     '#080E1C',
        card:    '#0F172A',
        sidebar: '#0A1020',
        input:   '#111827',
        border:  '#1E293B',
        teal: { DEFAULT: '#00D4C8', dim: '#00A8A0', glow: 'rgba(0,212,200,0.15)' },
        muted:   '#64748B',
        primary: '#F1F5F9',
      },
      boxShadow: {
        'teal-glow': '0 0 20px rgba(0,212,200,0.25)',
        'card':      '0 1px 3px rgba(0,0,0,0.5)',
      },
    },
  },
  plugins: [require('@tailwindcss/forms')],
};

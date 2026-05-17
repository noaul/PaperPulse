/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        paper: {
          primary: '#5265ff',
          info: '#00a6fb',
          success: '#14b8a6',
          warning: '#f59e0b',
          danger: '#f43f5e',
        },
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
}

/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: { 50: '#f0f4ff', 100: '#dbe4ff', 200: '#bac8ff', 500: '#4c6ef5', 600: '#4263eb', 700: '#3b5bdb', 800: '#364fc7', 900: '#2b3cb3' },
        accent: { 400: '#ffa94d', 500: '#ff922b', 600: '#fd7e14' },
      },
    },
  },
  plugins: [],
};

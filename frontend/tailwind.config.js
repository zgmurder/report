/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,ts}'],
  theme: {
    extend: {},
  },
  corePlugins: {
    // 避免覆盖现有 global.css 的基础重置
    preflight: false,
  },
  plugins: [],
}

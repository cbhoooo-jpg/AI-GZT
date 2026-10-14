import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  // 阶段1（前端重构 · 决策C①）:构建产物改相对路径引用
  //  —— 默认 base 为 '/'，产物 index.html 内引用 /assets/*（绝对路径），
  //     挂载到 FastAPI 子路径 /webapp 下会全部 404，导致整站白屏；
  //  —— base:'./' 后引用变为 ./assets/*，任意子路径挂载均可正常加载。
  base: './',
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  // 阶段2（模型配置模块）:开发模式代理，把前端 /api/* 请求转发到后端
  //  —— 生产环境:打包产物由 api_server.py 的 StaticFiles 挂载到 /webapp，前后端同源，无需代理；
  //  —— 开发环境:vite dev server 端口与后端不同，通过 proxy 转发避免跨域，保持前后端代码零差异；
  //  —— 目标端口与 api_server.py 的 DEFAULT_PORT 保持一致（8000）。
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      // 【主题统一·L1-②】主题令牌与主题工具走 /static 单一数据源（方式A:不复制文件）:
      //  —— dev 环境（npm run dev）:本代理转发 /static/* 到后端 8000，实时读根目录源文件（与 /api 代理完全同构）；
      //  —— prod 环境:打包产物由 api_server.py 的 StaticFiles 挂载 /webapp，前端页面的绝对路径 /static/* 正好命中后端 mount（旧前端 11 页已验证）。
      //  —— 注意:base:'./' 只重写相对路径引用，绝对路径 /static/* 不重写，故 dev 必须补这条代理，否则 theme.css / theme.js 404。
      '/static': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vue: ['vue', 'vue-router'],
        },
      },
    },
  },
})

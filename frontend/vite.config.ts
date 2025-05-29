import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueJsx(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  server: {
    // 应该在这里配置 host 和 port，它们是 server 对象的直接属性
    host: '127.0.0.1', // <-- 这一行是正确的，位置也正确
    port: 5050,      // <-- 这是您 Vite 前端的默认端口，请确保和 Flask 后端端口区分开
                     //     如果您想让Vite前端运行在5050，那就改成 5050
    proxy: {
      // 代理配置应该在这里，例如：
      // '/api': {
      //   target: 'http://127.0.0.1:5051', // 这是您的 Flask 后端地址
      //   changeOrigin: true,
      //   rewrite: (path) => path.replace(/^\/api/, '')
      // }
    }
  }
})

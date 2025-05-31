import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Toast, { POSITION } from 'vue-toastification'
import 'vue-toastification/dist/index.css'

import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'

const app = createApp(App)

// 配置 Toast
app.use(Toast, {
  position: POSITION.TOP_RIGHT,
  timeout: 3000,
  closeOnClick: true,
  pauseOnHover: true,
  draggable: true,
  dragOffset: 50,
  showIcon: true,
  maxToasts: 5,
  newestOnTop: true
})

// 配置 Pinia
app.use(createPinia())

// 全局错误处理
app.config.errorHandler = (err, vm, info) => {
  // 重要错误仍然记录到控制台，便于调试
  if (err instanceof Error && err.message.includes('network')) {
    console.error('Network error detected:', err)
  }
}

// 全局警告处理（生产环境可以完全关闭）
app.config.warnHandler = (msg, vm, trace) => {
  // 生产环境静默处理警告
  if (import.meta.env.DEV) {
    console.warn('Vue warning:', msg)
  }
}

// 配置路由
app.use(router)

// 初始化认证状态
const initAuth = async () => {
  const authStore = useAuthStore()
  try {
    await authStore.checkAuth()
  } catch (error) {
    // 静默处理初始认证检查失败
  }
}

// 挂载应用
initAuth().then(() => {
  app.mount('#app')
})

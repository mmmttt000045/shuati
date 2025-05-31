import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Toast, { POSITION } from 'vue-toastification'
import 'vue-toastification/dist/index.css'

import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'

const app = createApp(App)

app.use(createPinia())
app.use(router)

// Configure vue-toastification
app.use(Toast, {
  position: POSITION.TOP_RIGHT,
  timeout: 4000,
  closeOnClick: true,
  pauseOnFocusLoss: true,
  pauseOnHover: true,
  draggable: true,
  draggablePercent: 0.6,
  showCloseButtonOnHover: false,
  hideProgressBar: false,
  closeButton: "button",
  icon: true,
  rtl: false
})

// Global error handler
app.config.errorHandler = (err, vm, info) => {
  console.error('Global error:', err)
  console.error('Component:', vm)
  console.error('Error info:', info)
}

// Global warning handler
app.config.warnHandler = (msg, vm, trace) => {
  console.warn('Global warning:', msg)
  console.warn('Component:', vm)
  console.warn('Trace:', trace)
}

// Initialize authentication on app startup
async function initApp() {
  const authStore = useAuthStore()
  
  try {
    // Check if user is already authenticated
    await authStore.checkAuth()
  } catch (error) {
    console.error('Failed to check authentication status:', error)
  }
  
  app.mount('#app')
}

initApp()

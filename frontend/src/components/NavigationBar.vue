<template>
  <nav class="navigation-bar" ref="navRef">
    <div class="nav-container">
      <!-- 左侧：品牌标识和主导航 -->
      <div class="nav-left">
        <div class="brand">
          <button class="brand-link" @click="$emit('navigate', 'home')">
            <div class="brand-icon">📚</div>
            <span class="brand-text">MT题库练习系统</span>
          </button>
        </div>
        
        <!-- 移动端菜单按钮 -->
        <button 
          class="mobile-menu-toggle"
          @click="toggleMobileMenu"
          :class="{ active: showMobileMenu }"
          aria-label="切换菜单"
        >
          <span class="hamburger-line"></span>
          <span class="hamburger-line"></span>
          <span class="hamburger-line"></span>
        </button>
        
        <!-- 主导航菜单 -->
        <div class="nav-menu" :class="{ 'mobile-open': showMobileMenu }">
          <button 
            class="nav-item"
            :class="{ active: currentView === 'home' }"
            @click="handleNavigate('home')"
          >
            <span class="nav-icon">🎯</span>
            <span class="nav-text">题目练习</span>
          </button>
          
          <!-- VIP功能菜单 -->
          <div 
            v-if="isVipOrAdmin" 
            class="nav-item dropdown"
            ref="vipDropdownRef"
            :class="{ active: showVipMenu }"
          >
            <button 
              class="nav-link dropdown-trigger"
              @click="toggleVipMenu"
              @keydown.enter="toggleVipMenu"
              @keydown.escape="closeVipMenu"
              :aria-expanded="showVipMenu"
              aria-haspopup="true"
            >
              <span class="nav-icon">⭐</span>
              <span class="nav-text">VIP功能</span>
              <span class="dropdown-arrow" :class="{ rotated: showVipMenu }">▼</span>
            </button>
            
            <div 
              v-show="showVipMenu" 
              class="dropdown-menu"
              role="menu"
              @keydown.escape="closeVipMenu"
            >
              <button 
                class="dropdown-item"
                :class="{ active: currentView === 'vip-stats' }"
                role="menuitem"
                @click="handleNavigate('vip-stats')"
              >
                <span class="item-icon">📊</span>
                学习统计
              </button>
              <button 
                class="dropdown-item"
                :class="{ active: currentView === 'vip-export' }"
                role="menuitem"
                @click="handleNavigate('vip-export')"
              >
                <span class="item-icon">📄</span>
                错题导出
              </button>
              <button 
                class="dropdown-item"
                :class="{ active: currentView === 'vip-collections' }"
                role="menuitem"
                @click="handleNavigate('vip-collections')"
              >
                <span class="item-icon">⭐</span>
                错题集管理
              </button>
            </div>
          </div>
          
          <!-- 管理员功能 -->
          <button 
            v-if="isAdmin" 
            class="nav-item admin-item"
            :class="{ active: currentView === 'admin' }"
            @click="handleNavigate('admin')"
          >
            <span class="nav-icon">⚙️</span>
            <span class="nav-text">系统管理</span>
          </button>
        </div>
      </div>
      
      <!-- 右侧：用户信息和操作 -->
      <div class="nav-right">
        <div class="user-section" ref="userMenuRef">
          <!-- 用户信息 -->
          <div class="user-info" @click="toggleUserMenu">
            <div class="user-avatar">
              <span class="avatar-text">{{ getUserInitial() }}</span>
            </div>
            
            <div class="user-details">
              <span class="username">{{ authStore.user?.username }}</span>
              <UserBadge v-if="authStore.user" :model="authStore.user.model" />
            </div>
          </div>
          
          <!-- 用户菜单下拉 -->
          <button 
            class="user-menu-trigger"
            @click="toggleUserMenu"
            @keydown.enter="toggleUserMenu"
            @keydown.escape="closeUserMenu"
            :aria-expanded="showUserMenu"
            aria-haspopup="true"
            aria-label="用户菜单"
          >
            <span class="menu-arrow" :class="{ rotated: showUserMenu }">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M7 10L12 15L17 10" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </span>
          </button>
          
          <!-- 用户菜单 -->
          <div 
            v-show="showUserMenu" 
            class="user-menu"
            role="menu"
            @keydown.escape="closeUserMenu"
          >
            <!-- 用户信息头部 -->
            <div class="menu-user-header">
              <div class="menu-user-avatar">
                <span class="menu-avatar-text">{{ getUserInitial() }}</span>
              </div>
              <div class="menu-user-info">
                <div class="menu-username">{{ authStore.user?.username }}</div>
                <div class="menu-user-email">{{ getUserEmail() }}</div>
                <UserBadge v-if="authStore.user" :model="authStore.user.model" />
              </div>
            </div>
            
            <div class="menu-divider"></div>
            
            <!-- 菜单项 -->
            <router-link 
              to="/profile" 
              class="menu-item"
              role="menuitem"
              @click="closeUserMenu"
            >
              <span class="item-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M20 21V19C20 17.9391 19.5786 16.9217 18.8284 16.1716C18.0783 15.4214 17.0609 15 16 15H8C6.93913 15 5.92172 15.4214 5.17157 16.1716C4.42143 16.9217 4 17.9391 4 19V21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  <circle cx="12" cy="7" r="4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </span>
              <span class="item-content">
                <span class="item-title">个人资料</span>
                <span class="item-desc">管理您的个人信息</span>
              </span>
            </router-link>
            
            <router-link 
              to="/settings" 
              class="menu-item"
              role="menuitem"
              @click="closeUserMenu"
            >
              <span class="item-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="2"/>
                  <path d="M12 1V3M12 21V23M4.22 4.22L5.64 5.64M18.36 18.36L19.78 19.78M1 12H3M21 12H23M4.22 19.78L5.64 18.36M18.36 5.64L19.78 4.22" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
              </span>
              <span class="item-content">
                <span class="item-title">系统设置</span>
                <span class="item-desc">偏好设置和配置</span>
              </span>
            </router-link>
            
            <div class="menu-item" role="menuitem" @click="toggleTheme">
              <span class="item-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </span>
              <span class="item-content">
                <span class="item-title">主题切换</span>
                <span class="item-desc">切换深色/浅色模式</span>
              </span>
            </div>
            
            <div class="menu-divider"></div>
            
            <button 
              class="menu-item logout-item" 
              @click="handleLogout"
              role="menuitem"
            >
              <span class="item-icon logout-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M9 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V5C3 4.46957 3.21071 3.96086 3.58579 3.58579C3.96086 3.21071 4.46957 3 5 3H9" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  <polyline points="16,17 21,12 16,7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  <line x1="21" y1="12" x2="9" y2="12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </span>
              <span class="item-content">
                <span class="item-title">退出登录</span>
                <span class="item-desc">安全退出系统</span>
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 移动端菜单遮罩 -->
    <div 
      v-if="showMobileMenu" 
      class="mobile-overlay"
      @click="closeMobileMenu"
    ></div>
  </nav>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { USER_MODEL } from '@/types'
import UserBadge from './UserBadge.vue'

// Props
interface Props {
  currentView?: string
}

const props = withDefaults(defineProps<Props>(), {
  currentView: 'home'
})

// Emits
const emit = defineEmits<{
  navigate: [view: string]
}>()

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

// DOM引用
const navRef = ref<HTMLElement>()
const vipDropdownRef = ref<HTMLElement>()
const userMenuRef = ref<HTMLElement>()

// 响应式状态
const showVipMenu = ref(false)
const showUserMenu = ref(false)
const showMobileMenu = ref(false)

// 计算属性
const isVipOrAdmin = computed(() => {
  const model = authStore.user?.model
  return model === USER_MODEL.VIP || model === USER_MODEL.ROOT
})

const isAdmin = computed(() => {
  return authStore.user?.model === USER_MODEL.ROOT
})

// 方法
const getUserInitial = () => {
  return authStore.user?.username?.charAt(0).toUpperCase() || 'U'
}

const getUserEmail = () => {
  return `${authStore.user?.username || 'user'}@example.com`
}

const toggleTheme = () => {
  // 这里可以实现主题切换逻辑
  const currentTheme = document.documentElement.getAttribute('data-theme')
  const newTheme = currentTheme === 'dark' ? 'light' : 'dark'
  document.documentElement.setAttribute('data-theme', newTheme)
  localStorage.setItem('theme', newTheme)
}

// 导航处理
const handleNavigate = (view: string) => {
  emit('navigate', view)
  closeAllMenus()
}

// VIP菜单控制
const toggleVipMenu = () => {
  showVipMenu.value = !showVipMenu.value
  if (showVipMenu.value) {
    showUserMenu.value = false
  }
}

const closeVipMenu = () => {
  showVipMenu.value = false
}

// 用户菜单控制
const toggleUserMenu = () => {
  showUserMenu.value = !showUserMenu.value
  if (showUserMenu.value) {
    showVipMenu.value = false
  }
}

const closeUserMenu = () => {
  showUserMenu.value = false
}

// 移动端菜单控制
const toggleMobileMenu = () => {
  showMobileMenu.value = !showMobileMenu.value
  // 防止页面滚动
  if (showMobileMenu.value) {
    document.body.style.overflow = 'hidden'
  } else {
    document.body.style.overflow = ''
  }
}

const closeMobileMenu = () => {
  showMobileMenu.value = false
  document.body.style.overflow = ''
}

// 关闭所有菜单
const closeAllMenus = () => {
  showVipMenu.value = false
  showUserMenu.value = false
  closeMobileMenu()
}

// 点击外部关闭菜单
const handleClickOutside = (event: MouseEvent) => {
  const target = event.target as Node
  
  // 检查VIP下拉菜单
  if (showVipMenu.value && vipDropdownRef.value && !vipDropdownRef.value.contains(target)) {
    closeVipMenu()
  }
  
  // 检查用户菜单
  if (showUserMenu.value && userMenuRef.value && !userMenuRef.value.contains(target)) {
    closeUserMenu()
  }
}

// 键盘导航
const handleKeyDown = (event: KeyboardEvent) => {
  if (event.key === 'Escape') {
    closeAllMenus()
  }
}

// 路由变化时关闭移动端菜单
const handleRouteChange = () => {
  closeMobileMenu()
}

// 登出处理
const handleLogout = async () => {
  try {
    await authStore.logout()
    closeAllMenus()
    router.push('/login')
  } catch (error) {
    console.error('登出失败:', error)
  }
}

// 响应式处理
const handleResize = () => {
  if (window.innerWidth > 768 && showMobileMenu.value) {
    closeMobileMenu()
  }
}

// 生命周期
onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  document.addEventListener('keydown', handleKeyDown)
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  document.removeEventListener('keydown', handleKeyDown)
  window.removeEventListener('resize', handleResize)
  document.body.style.overflow = ''
})

// 监听路由变化
router.afterEach(handleRouteChange)
</script>

<style scoped>
.navigation-bar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  position: sticky;
  top: 0;
  z-index: 1000;
  box-shadow: 0 2px 20px rgba(0, 0, 0, 0.1);
}

.nav-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 1.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 72px;
  position: relative;
}

/* 左侧区域 */
.nav-left {
  display: flex;
  align-items: center;
  gap: 2rem;
  flex: 1;
}

.brand {
  flex-shrink: 0;
}

.brand-link {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: none;
  border: none;
  color: white;
  font-weight: 600;
  font-size: 1.3rem;
  transition: all 0.3s ease;
  cursor: pointer;
  padding: 0.75rem 1rem;
  border-radius: 10px;
}

.brand-link:hover {
  transform: translateY(-1px);
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  background: rgba(255, 255, 255, 0.1);
}

.brand-icon {
  font-size: 1.75rem;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
}

.brand-text {
  color: white;
}

/* 移动端菜单按钮 */
.mobile-menu-toggle {
  display: none;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  width: 44px;
  height: 44px;
  background: none;
  border: none;
  cursor: pointer;
  padding: 10px;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.mobile-menu-toggle:hover {
  background: rgba(255, 255, 255, 0.1);
}

.hamburger-line {
  width: 24px;
  height: 2px;
  background: white;
  margin: 2px 0;
  transition: all 0.3s ease;
  border-radius: 1px;
}

.mobile-menu-toggle.active .hamburger-line:nth-child(1) {
  transform: rotate(45deg) translate(5px, 5px);
}

.mobile-menu-toggle.active .hamburger-line:nth-child(2) {
  opacity: 0;
}

.mobile-menu-toggle.active .hamburger-line:nth-child(3) {
  transform: rotate(-45deg) translate(7px, -6px);
}

/* 导航菜单 */
.nav-menu {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.875rem 1.25rem;
  color: rgba(255, 255, 255, 0.9);
  background: none;
  border: none;
  border-radius: 10px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  font-size: 1rem;
}

.nav-item:hover,
.nav-item.active {
  background: rgba(255, 255, 255, 0.15);
  color: white;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.25);
}

.nav-item.admin-item {
  background: linear-gradient(45deg, #ff6b6b, #ee5a52);
  color: white;
}

.nav-item.admin-item:hover,
.nav-item.admin-item.active {
  background: linear-gradient(45deg, #ff5252, #e53935);
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(255, 107, 107, 0.4);
}

.nav-icon {
  font-size: 1.2rem;
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.2));
  flex-shrink: 0;
}

.nav-text {
  font-size: 1rem;
  letter-spacing: 0.02em;
}

/* 下拉菜单 */
.dropdown {
  position: relative;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.875rem 1.25rem;
  color: rgba(255, 255, 255, 0.9);
  border-radius: 10px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  font-weight: 500;
  cursor: pointer;
  background: none;
  border: none;
  white-space: nowrap;
  font-size: 1rem;
}

.nav-link:hover,
.dropdown.active .nav-link {
  background: rgba(255, 255, 255, 0.15);
  color: white;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.25);
}

.dropdown-arrow {
  font-size: 0.8rem;
  transition: transform 0.2s ease;
  margin-left: 0.25rem;
  opacity: 0.8;
}

.dropdown-arrow.rotated {
  transform: rotate(180deg);
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + 10px);
  left: 0;
  background: white;
  border-radius: 14px;
  box-shadow: 0 12px 48px rgba(0, 0, 0, 0.18);
  padding: 0.75rem 0;
  min-width: 220px;
  border: 1px solid rgba(0, 0, 0, 0.05);
  z-index: 1001;
  transform: translateY(-15px) scale(0.95);
  opacity: 0;
  visibility: hidden;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.dropdown.active .dropdown-menu {
  transform: translateY(0) scale(1);
  opacity: 1;
  visibility: visible;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 0.875rem;
  padding: 0.875rem 1.25rem;
  color: #374151;
  background: none;
  border: none;
  width: 100%;
  text-align: left;
  transition: all 0.2s ease;
  font-weight: 500;
  cursor: pointer;
  font-size: 1rem;
  position: relative;
}

.dropdown-item:hover,
.dropdown-item.active {
  background: linear-gradient(90deg, #f8fafc, #f1f5f9);
  color: #1f2937;
  transform: translateX(4px);
}

.dropdown-item.active {
  background: linear-gradient(90deg, #eff6ff, #dbeafe);
  color: #2563eb;
  border-left: 4px solid #3b82f6;
  padding-left: calc(1.25rem - 4px);
}

.dropdown-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: linear-gradient(180deg, #3b82f6, #1d4ed8);
  border-radius: 0 2px 2px 0;
}

.item-icon {
  font-size: 1.1rem;
  width: 1.4rem;
  text-align: center;
  flex-shrink: 0;
}

/* 右侧用户区域 */
.nav-right {
  display: flex;
  align-items: center;
}

.user-section {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.user-info:hover {
  background: rgba(255, 255, 255, 0.1);
}

.user-avatar {
  width: 40px;
  height: 40px;
  background: linear-gradient(45deg, #4f46e5, #7c3aed);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  flex-shrink: 0;
}

.avatar-text {
  color: white;
  font-weight: 600;
  font-size: 1rem;
}

.user-details {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 0.5rem;
}

.username {
  color: white;
  font-weight: 600;
  font-size: 0.95rem;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.user-menu-trigger {
  padding: 0.5rem;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.2s ease;
  color: rgba(255, 255, 255, 0.8);
  outline: none;
  background: none;
  border: none;
}

.user-menu-trigger:hover,
.user-menu-trigger:focus {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.menu-arrow {
  font-size: 0.7rem;
  transition: transform 0.3s ease;
}

.menu-arrow.rotated {
  transform: rotate(180deg);
}

.user-menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  background: white;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
  padding: 0.5rem 0;
  min-width: 180px;
  border: 1px solid rgba(0, 0, 0, 0.05);
  z-index: 1001;
  opacity: 0;
  transform: translateY(-10px);
  animation: fadeInDown 0.3s ease forwards;
}

.menu-user-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
}

.menu-user-avatar {
  width: 40px;
  height: 40px;
  background: linear-gradient(45deg, #4f46e5, #7c3aed);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  flex-shrink: 0;
}

.menu-avatar-text {
  color: white;
  font-weight: 600;
  font-size: 1rem;
}

.menu-user-info {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.menu-username {
  color: #374151;
  font-weight: 600;
  font-size: 0.95rem;
}

.menu-user-email {
  color: #6b7280;
  font-weight: 500;
  font-size: 0.85rem;
}

.menu-divider {
  height: 1px;
  background: #e5e7eb;
  margin: 0.5rem 0;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  color: #374151;
  text-decoration: none;
  transition: all 0.2s ease;
  font-weight: 500;
  border: none;
  background: none;
  width: 100%;
  text-align: left;
  cursor: pointer;
  font-size: 0.95rem;
}

.menu-item:hover {
  background: #f8fafc;
  color: #1f2937;
}

.item-icon {
  font-size: 1rem;
  width: 1.2rem;
  text-align: center;
  flex-shrink: 0;
}

.item-content {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.item-title {
  font-weight: 600;
  font-size: 0.95rem;
}

.item-desc {
  font-size: 0.8rem;
  color: #6b7280;
  font-weight: 400;
}

.logout-item:hover {
  background: #fef2f2;
  color: #dc2626;
}

.logout-item:hover .item-desc {
  color: #fca5a5;
}

/* 移动端遮罩 */
.mobile-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 999;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .nav-container {
    padding: 0 1rem;
    height: 64px;
  }
  
  .brand-text {
    display: none;
  }
  
  .mobile-menu-toggle {
    display: flex;
  }
  
  .nav-menu {
    position: fixed;
    top: 64px;
    left: 0;
    right: 0;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    flex-direction: column;
    align-items: stretch;
    padding: 1.5rem;
    gap: 0.75rem;
    transform: translateY(-100%);
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    z-index: 1000;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
  }
  
  .nav-menu.mobile-open {
    transform: translateY(0);
  }
  
  .nav-item {
    justify-content: flex-start;
    padding: 1.25rem 1.5rem;
    border-radius: 12px;
    margin-bottom: 0.5rem;
    font-size: 1.1rem;
  }
  
  .dropdown-menu {
    position: static;
    box-shadow: none;
    background: rgba(255, 255, 255, 0.12);
    border: 1px solid rgba(255, 255, 255, 0.2);
    margin-top: 0.75rem;
    border-radius: 12px;
    transform: none;
    opacity: 1;
    visibility: visible;
    transition: none;
  }
  
  .dropdown-item {
    color: rgba(255, 255, 255, 0.9);
    padding: 1rem 1.5rem;
  }
  
  .dropdown-item:hover,
  .dropdown-item.active {
    background: rgba(255, 255, 255, 0.15);
    color: white;
    transform: none;
    border-left: none;
    padding-left: 1.5rem;
  }
  
  .dropdown-item.active::before {
    display: none;
  }
  
  .user-details {
    display: none;
  }
  
  .user-menu {
    right: 1rem;
  }
}

@media (max-width: 640px) {
  .nav-container {
    padding: 0 0.75rem;
    height: 60px;
  }
  
  .nav-menu {
    top: 60px;
    padding: 1.25rem;
  }
  
  .dropdown-menu,
  .user-menu {
    min-width: 180px;
  }
  
  .user-menu {
    right: 0.75rem;
  }
}

@media (max-width: 480px) {
  .nav-container {
    height: 56px;
  }
  
  .nav-menu {
    top: 56px;
    padding: 1rem;
  }
  
  .brand-icon {
    font-size: 1.5rem;
  }
  
  .user-avatar {
    width: 36px;
    height: 36px;
  }
  
  .avatar-text {
    font-size: 0.9rem;
  }
}

/* 高对比度模式支持 */
@media (prefers-contrast: high) {
  .navigation-bar {
    background: #000;
    border-bottom: 2px solid #fff;
  }
  
  .nav-item:hover,
  .nav-item.active {
    background: #fff;
    color: #000;
  }
  
  .dropdown-menu,
  .user-menu {
    border: 2px solid #000;
  }
}

/* 减少动画效果 */
@media (prefers-reduced-motion: reduce) {
  .nav-item,
  .nav-link,
  .dropdown-arrow,
  .menu-arrow,
  .dropdown-menu,
  .user-menu,
  .mobile-menu-toggle,
  .hamburger-line {
    transition: none;
  }
  
  .dropdown-menu,
  .user-menu {
    animation: none;
  }
}

/* 焦点样式 */
.nav-item:focus,
.nav-link:focus,
.user-menu-trigger:focus,
.menu-item:focus,
.dropdown-item:focus {
  outline: 2px solid rgba(255, 255, 255, 0.8);
  outline-offset: 2px;
}

/* 深色模式支持 */
@media (prefers-color-scheme: dark) {
  .dropdown-menu,
  .user-menu {
    background: #1f2937;
    border-color: #374151;
  }
  
  .dropdown-item,
  .menu-item {
    color: #e5e7eb;
  }
  
  .dropdown-item:hover,
  .menu-item:hover {
    background: #374151;
    color: #f9fafb;
  }
  
  .logout-item:hover {
    background: #7f1d1d;
    color: #fca5a5;
  }
  
  .menu-divider {
    background: #4b5563;
  }
}
</style> 
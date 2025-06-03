<template>
  <v-app-bar
    app
    fixed
    elevate-on-scroll
    :elevation="2"
    height="72"
    class="navigation-bar"
    ref="navRef"
  >
    <v-container fluid class="nav-container d-flex align-center pa-0 px-md-4">
      <div class="d-flex align-center" style="min-width: 0;">
        <div class="brand-section d-flex align-center mr-2 mr-lg-6">
          <v-btn
            icon
            variant="text"
            class="brand-icon-btn"
            @click="$emit('navigate', 'home')"
            aria-label="主页"
          >
            <span class="brand-icon">📚</span>
          </v-btn>
          <v-app-bar-title class="brand-text-container">
            <span class="brand-text hidden-sm-and-down">MT题库练习系统</span>
            <span class="brand-text-short hidden-md-and-up hidden-xs">MT题库</span>
            <span class="brand-text-short d-inline d-sm-none">MT</span> </v-app-bar-title>
        </div>

        <v-app-bar-nav-icon
          class="mobile-menu-toggle hidden-lg-and-up"
          @click.stop="toggleMobileMenu"
          aria-label="切换菜单"
        >
          <span class="hamburger-icon">
            <span class="hamburger-line" :class="{ active: showMobileMenu }"></span>
            <span class="hamburger-line" :class="{ active: showMobileMenu }"></span>
            <span class="hamburger-line" :class="{ active: showMobileMenu }"></span>
          </span>
        </v-app-bar-nav-icon>
      </div>

      <div class="nav-menu-container d-none d-lg-flex flex-grow-1 justify-center">
        <div class="nav-menu d-flex align-center justify-space-evenly">
          <v-btn
            variant="text"
            class="nav-item"
            :class="{ active: currentView === 'home' }"
            @click="handleNavigate('home')"
          >
            <template #prepend><span class="nav-icon">🎯</span></template>
            <span class="nav-text">题目练习</span>
          </v-btn>

          <!-- 使用统计按钮 - 直接导航到增强统计页面 -->
          <v-btn
            variant="text"
            class="nav-item"
            :class="{ active: currentView === 'stats' }"
            @click="handleNavigate('stats')"
          >
            <template #prepend><IconStats :size="18" color="currentColor" class="nav-icon-svg" /></template>
            <span class="nav-text">使用统计</span>
          </v-btn>

          <v-menu
            v-if="isVipOrAdmin"
            v-model="showVipMenu"
            :close-on-content-click="false"
            location="bottom"
            transition="slide-y-transition"
            offset="10"
          >
            <template #activator="{ props: menuProps }">
              <v-btn
                variant="text"
                class="nav-item dropdown"
                :class="{ active: showVipMenu }"
                v-bind="menuProps"
              >
                <template #prepend><span class="nav-icon">⭐</span></template>
                <span class="nav-text">VIP功能</span>
                <template #append>
                  <v-icon class="dropdown-arrow" :class="{ rotated: showVipMenu }" size="small">
                    mdi-chevron-down
                  </v-icon>
                </template>
              </v-btn>
            </template>
            <v-card class="dropdown-menu" elevation="8" rounded="lg">
              <v-list nav density="comfortable">
                <v-list-item
                  v-for="item in vipMenuItems"
                  :key="item.view"
                  class="dropdown-item"
                  :class="{ active: currentView === item.view }"
                  @click="handleNavigate(item.view)"
                  :prepend-icon="item.icon"
                >
                  <v-list-item-title>{{ item.title }}</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-card>
          </v-menu>

          <v-btn
            v-if="isAdmin"
            variant="text"
            class="nav-item admin-item"
            :class="{ active: currentView === 'admin' }"
            @click="handleNavigate('admin')"
          >
            <template #prepend><span class="nav-icon">⚙️</span></template>
            <span class="nav-text">系统管理</span>
          </v-btn>
        </div>
      </div>

      <div class="nav-right ml-auto flex-shrink-0">
        <v-menu
          v-model="showUserMenu"
          :close-on-content-click="false"
          location="bottom end"
          transition="slide-y-transition"
          offset="8"
        >
          <template #activator="{ props: menuProps }">
            <v-btn
              variant="text"
              class="user-section d-flex align-center"
              v-bind="menuProps"
              height="auto" min-height="40" 
            >
              <v-avatar
                :size="$vuetify.display.xs ? 32 : 40"
                class="user-avatar mr-0 mr-sm-2"
              >
                <span class="avatar-text">{{ getUserInitial() }}</span>
              </v-avatar>
              <div class="user-details hidden-md-and-down mr-2">
                <span class="username">{{ authStore.user?.username }}</span>
                <UserBadge v-if="authStore.user" :model="authStore.user.model" />
              </div>
              <v-icon class="menu-arrow hidden-xs-only" :class="{ rotated: showUserMenu }" size="small">
                mdi-chevron-down
              </v-icon>
            </v-btn>
          </template>

          <v-card class="user-menu" elevation="8" rounded="lg" min-width="260">
            <v-card-item class="menu-user-header">
              <template #prepend>
                <v-avatar size="40" class="menu-user-avatar">
                  <span class="menu-avatar-text">{{ getUserInitial() }}</span>
                </v-avatar>
              </template>
              <v-card-title class="menu-username">{{ authStore.user?.username }}</v-card-title>
              <v-card-subtitle class="menu-user-email">{{ getUserEmail() }}</v-card-subtitle>
              <template #append>
                <UserBadge v-if="authStore.user" :model="authStore.user.model" />
              </template>
            </v-card-item>
            <v-divider></v-divider>
            <v-list nav density="comfortable">
              <template v-for="(item, index) in userMenuItems" :key="index">
                <v-divider v-if="item.type === 'divider'" class="my-2"></v-divider>
                <v-list-item
                  v-else
                  class="menu-item"
                  :class="item.class"
                  @click="item.action"
                  :prepend-icon="item.icon"
                >
                  <div class="item-content">
                    <v-list-item-title class="item-title">{{ item.title }}</v-list-item-title>
                    <v-list-item-subtitle class="item-desc">{{ item.desc }}</v-list-item-subtitle>
                  </div>
                </v-list-item>
              </template>
            </v-list>
          </v-card>
        </v-menu>
      </div>
    </v-container>
  </v-app-bar>

  <v-navigation-drawer
    v-model="showMobileMenu"
    temporary
    location="left"
    width="300"
    class="mobile-nav-drawer"
  >
    <v-list nav>
      <v-list-item class="mobile-user-header">
        <template #prepend>
          <v-avatar size="48" class="user-avatar">
            <span class="avatar-text">{{ getUserInitial() }}</span>
          </v-avatar>
        </template>
        <v-list-item-title class="username">{{ authStore.user?.username }}</v-list-item-title>
        <v-list-item-subtitle>
          <UserBadge v-if="authStore.user" :model="authStore.user.model" />
        </v-list-item-subtitle>
      </v-list-item>
      <v-divider></v-divider>

      <v-list-item
        class="mobile-nav-item"
        :class="{ active: currentView === 'home' }"
        @click="handleNavigate('home')"
        prepend-icon="mdi-target"
      >
        <v-list-item-title>题目练习</v-list-item-title>
      </v-list-item>

      <!-- 移动端使用统计 -->
      <v-list-item
        class="mobile-nav-item"
        :class="{ active: currentView === 'stats' }"
        @click="handleNavigate('stats')"
      >
        <template #prepend>
          <IconStats :size="20" color="currentColor" class="mobile-nav-icon-svg" />
        </template>
        <v-list-item-title>使用统计</v-list-item-title>
      </v-list-item>

      <v-list-group v-if="isVipOrAdmin" value="vip">
        <template #activator="{ props: groupProps }">
          <v-list-item
            v-bind="groupProps"
            class="mobile-nav-item"
            prepend-icon="mdi-star-outline"
          >
            <v-list-item-title>VIP功能</v-list-item-title>
          </v-list-item>
        </template>
        <v-list-item
          v-for="item in vipMenuItems"
          :key="`mobile-${item.view}`"
          class="mobile-nav-item mobile-nav-sub-item"
          :class="{ active: currentView === item.view }"
          @click="handleNavigate(item.view)"
          :prepend-icon="item.icon"
        >
          <v-list-item-title>{{ item.title }}</v-list-item-title>
        </v-list-item>
      </v-list-group>

      <v-list-item
        v-if="isAdmin"
        class="mobile-nav-item admin-item"
        :class="{ active: currentView === 'admin' }"
        @click="handleNavigate('admin')"
        prepend-icon="mdi-cog-outline"
      >
        <v-list-item-title>系统管理</v-list-item-title>
      </v-list-item>
    </v-list>
  </v-navigation-drawer>
</template>

<script setup lang="ts">
import { ref, computed, onMounted,  watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useTheme } from 'vuetify'
import { useAuthStore } from '@/stores/auth'
import { USER_MODEL } from '@/types'
import UserBadge from '@/components/common/UserBadge.vue'
import IconStats from '@/components/icons/IconStats.vue'

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
const authStore = useAuthStore()
const vuetifyTheme = useTheme()

// DOM引用
const navRef = ref<HTMLElement | undefined>() // Or ComponentPublicInstance if it's a Vuetify component ref

// Responsive state
const showVipMenu = ref(false)
const showUserMenu = ref(false)
const showMobileMenu = ref(false)

// Computed properties
const isVipOrAdmin = computed(() => {
  const model = authStore.user?.model
  return model === USER_MODEL.VIP || model === USER_MODEL.ROOT
})

const isAdmin = computed(() => {
  return authStore.user?.model === USER_MODEL.ROOT
})

// VIP Menu Items (Data-driven)
const vipMenuItems = ref([
  { title: '学习统计', icon: 'mdi-chart-bar', view: 'vip-stats' },
  { title: '错题导出', icon: 'mdi-file-document-outline', view: 'vip-export' },
  { title: '错题集管理', icon: 'mdi-star-box-multiple-outline', view: 'vip-collections' },
]);

// User Menu Items (Data-driven)
const userMenuItems = computed(() => [
  { title: '个人资料', icon: 'mdi-account-circle-outline', action: navigateToProfile, desc: '管理您的个人信息' },
  { title: '系统设置', icon: 'mdi-cog-outline', action: navigateToSettings, desc: '偏好设置和配置' },
  { 
    title: '主题切换', 
    icon: vuetifyTheme.global.current.value.dark ? 'mdi-weather-night' : 'mdi-weather-sunny', 
    action: toggleTheme, 
    desc: `切换到${vuetifyTheme.global.current.value.dark ? '浅色' : '深色'}模式` 
  },
  { type: 'divider' },
  { title: '退出登录', icon: 'mdi-logout', action: handleLogout, desc: '安全退出系统', class: 'logout-item' }
]);


// Methods
const getUserInitial = () => {
  return authStore.user?.username?.charAt(0).toUpperCase() || 'U'
}

const getUserEmail = () => {
  // Fallback for email, adjust if you have real email data
  return `${authStore.user?.username || 'user'}@example.com`
}

const toggleTheme = () => {
  const newThemeName = vuetifyTheme.global.current.value.dark ? 'light' : 'dark';
  vuetifyTheme.global.name.value = newThemeName;
  localStorage.setItem('theme', newThemeName); // Persist theme choice
  // User menu might automatically close due to re-render, or close it explicitly if needed
  // showUserMenu.value = false; // Only if it doesn't close automatically
}

const handleNavigate = (view: string) => {
  emit('navigate', view)
  closeAllMenus()
}

const navigateToProfile = () => {
  router.push('/profile')
  closeUserMenu()
}

const navigateToSettings = () => {
  router.push('/settings')
  closeUserMenu()
}

const closeUserMenu = () => {
  showUserMenu.value = false
}

const toggleMobileMenu = () => {
  showMobileMenu.value = !showMobileMenu.value
}

const closeMobileMenu = () => {
  showMobileMenu.value = false
}

const closeAllMenus = () => {
  showVipMenu.value = false
  showUserMenu.value = false
  closeMobileMenu()
}

const handleLogout = async () => {
  try {
    await authStore.logout()
    closeAllMenus()
    router.push('/login')
  } catch (error) {
    console.error('登出失败:', error)
    // Optionally show a notification to the user
  }
}

// Lifecycle & Watchers
onMounted(() => {
  // Load persisted theme
  const savedTheme = localStorage.getItem('theme');
  if (savedTheme && (savedTheme === 'light' || savedTheme === 'dark')) {
    vuetifyTheme.global.name.value = savedTheme;
  }
})

// Watch for route changes to close mobile menu
watch(() => router.currentRoute.value, () => {
  closeMobileMenu();
});

</script>

<style scoped>
/* 导航栏主体样式 */
.navigation-bar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
  backdrop-filter: blur(10px); /* Might need -webkit-backdrop-filter for Safari */
  border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
  box-shadow: 0 2px 20px rgba(0, 0, 0, 0.1) !important;
}

/* 导航容器 */
.nav-container {
  height: 72px; /* Ensure this aligns with v-app-bar height */
  max-width: 1400px; /* Or your desired max width */
  margin: 0 auto; /* Center container */
}

/* 导航菜单容器 - 新增 */
.nav-menu-container {
  max-width: 600px; /* 限制最大宽度，避免按钮过度分散 */
  min-width: 400px; /* 确保最小宽度，保持按钮间距 */
}

/* 响应式调整导航菜单容器 */
@media (max-width: 1200px) {
  .nav-menu-container {
    max-width: 500px;
    min-width: 350px;
  }
}

@media (max-width: 1024px) {
  .nav-menu-container {
    max-width: 450px;
    min-width: 300px;
  }
}

/* 导航菜单 - 更新 */
.nav-menu {
  width: 100%;
  gap: 0.5rem; /* 按钮之间的最小间距 */
}

/* 左侧区域flex grow and min-width:0 to prevent overflow with long brand names/many items */

/* 品牌区域 */
.brand-section {
  gap: 0.5rem; /* Vuetify spacing: gap-2 */
  flex-shrink: 0; /* Prevent brand from shrinking too much */
}
.brand-text-container {
  /* Allow title to shrink and show ellipsis if Vuetify handles it, or set explicit width */
  min-width: 50px; /* Adjust as needed */
}

/* 品牌图标按钮 */
.brand-icon-btn {
  color: white !important;
  transition: all 0.3s ease !important;
  width: 40px !important; /* Or use Vuetify's size props if preferred */
  height: 40px !important;
}
.brand-icon-btn:hover {
  background: rgba(255, 255, 255, 0.1) !important;
  transform: translateY(-1px);
}
.brand-icon {
  font-size: 1.5rem;
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
  transition: all 0.3s ease;
}
.brand-icon-btn:hover .brand-icon {
  transform: rotate(10deg) scale(1.1);
}

/* 品牌文字 */
.brand-text, .brand-text-short {
  color: white;
  font-weight: 600;
  text-shadow: 0 1px 2px rgba(0,0,0,0.2);
  user-select: none;
  cursor: default;
  white-space: nowrap;
  display: inline-block; /* Important for proper display with hidden-* classes */
}
.brand-text { font-size: 1.2rem; }
.brand-text-short { font-size: 1rem; }
.brand-text-container .d-inline.d-sm-none { font-size: 0.9rem; } /* smallest screens */


/* 移动端菜单按钮 (v-app-bar-nav-icon handles some styling) */
.mobile-menu-toggle {
  color: white !important;
  /* transition is handled by v-app-bar-nav-icon */
}
.mobile-menu-toggle:hover {
  background: rgba(255, 255, 255, 0.1) !important;
}
.hamburger-icon {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  width: 20px;
  height: 20px;
}
.hamburger-line {
  width: 16px;
  height: 2px;
  background: white;
  margin: 1.5px 0;
  transition: all 0.3s ease;
  border-radius: 1px;
}
.hamburger-line.active:nth-child(1) { transform: rotate(45deg) translate(4px, 4px); }
.hamburger-line.active:nth-child(2) { opacity: 0; }
.hamburger-line.active:nth-child(3) { transform: rotate(-45deg) translate(5px, -5px); }

/* 导航菜单项 */
.nav-item {
  color: rgba(255, 255, 255, 0.9) !important;
  text-transform: none !important;
  font-weight: 500 !important;
  transition: all 0.3s ease !important;
  border-radius: 8px !important;
  margin: 0 !important; /* 移除外边距，使用父容器的justify-space-evenly */
  min-width: 120px !important; /* 确保按钮有最小宽度 */
  flex: 0 1 auto !important; /* 允许按钮根据内容调整大小 */
}
.nav-item:hover,
.nav-item.active {
  background: rgba(255, 255, 255, 0.15) !important;
  color: white !important;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}
.nav-item.admin-item { /* Special style for admin button */
  background: linear-gradient(45deg, #ff6b6b, #ee5a52) !important;
  color: white !important;
}
.nav-item.admin-item:hover,
.nav-item.admin-item.active {
  background: linear-gradient(45deg, #ff5252, #e53935) !important;
  box-shadow: 0 6px 20px rgba(255, 107, 107, 0.4);
}
.nav-icon { /* Emoji icons */
  font-size: 1.1rem;
  filter: drop-shadow(0 1px 2px rgba(0,0,0,0.2));
  margin-right: 0.5em; /* if using template #prepend */
}
.nav-icon-svg { /* SVG icons */
  filter: drop-shadow(0 1px 2px rgba(0,0,0,0.2));
  transition: all 0.3s ease;
}
.nav-text {
  font-size: 0.9rem;
  letter-spacing: 0.02em;
}

/* 下拉箭头 */
.dropdown-arrow {
  transition: transform 0.3s ease !important;
  opacity: 0.8;
}
.dropdown-arrow.rotated {
  transform: rotate(180deg);
}

/* 下拉菜单 (v-menu content) */
.dropdown-menu { /* VIP dropdown */
  margin-top: 10px;
  border: 1px solid rgba(0,0,0,0.05);
  box-shadow: 0 8px 32px rgba(0,0,0,0.15) !important;
}
.dropdown-item {
  transition: all 0.2s ease !important;
  font-weight: 500 !important;
}
.dropdown-item :deep(.v-list-item-prepend) .v-icon { /* Style MDI icons in dropdown */
  margin-inline-end: 12px !important;
  font-size: 1.1rem;
  width: 1.4rem;
  text-align: center;
}
.dropdown-item:hover,
.dropdown-item.active {
  background: linear-gradient(90deg, #f8fafc, #f1f5f9) !important;
  color: #1f2937 !important;
  transform: translateX(4px);
}
.dropdown-item.active {
  background: linear-gradient(90deg, #eff6ff, #dbeafe) !important;
  color: #2563eb !important;
  border-left: 4px solid #3b82f6;
}


/* 用户区域 */
.user-section { /* This is the v-btn activator for user menu */
  color: white !important;
  text-transform: none !important;
  transition: all 0.3s ease !important;
  border-radius: 8px !important;
  padding: 4px 8px !important; /* Vuetify: pa-1 px-2 */
  /* min-width: auto !important; Removed, let content define or use Vuetify width utils */
}
.user-section:hover {
  background: rgba(255, 255, 255, 0.1) !important;
}
.user-avatar {
  background: linear-gradient(45deg, #4f46e5, #7c3aed) !important;
  border: 2px solid rgba(255,255,255,0.2);
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  flex-shrink: 0; /* Prevent avatar from shrinking */
}
.avatar-text, .menu-avatar-text {
  color: white;
  font-weight: 600;
}
.user-details {
  display: flex; /* Already a flex item, ensure children are aligned */
  flex-direction: row;
  align-items: center;
  gap: 0.5rem; /* Vuetify: gap-2 */
  min-width: 0; /* Allow shrinking */
  overflow: hidden; /* For text-overflow */
}
.username {
  color: white !important;
  font-weight: 600 !important;
  font-size: 0.9rem !important;
  text-shadow: 0 1px 2px rgba(0,0,0,0.2);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.menu-arrow { /* Chevron icon in user section */
  color: rgba(255, 255, 255, 0.8) !important;
  transition: transform 0.3s ease !important;
}
.menu-arrow.rotated {
  transform: rotate(180deg);
}

/* 用户菜单 (v-menu content) */
.user-menu {
  margin-top: 8px;
  border: 1px solid rgba(0,0,0,0.05);
  box-shadow: 0 8px 32px rgba(0,0,0,0.15) !important;
}
.menu-user-header {
  /* border-bottom: 1px solid #e5e7eb; Using v-divider instead */
}
.menu-user-avatar {
  background: linear-gradient(45deg, #4f46e5, #7c3aed) !important;
}
.menu-username {
  color: #374151 !important;
  font-weight: 600 !important;
  font-size: 0.95rem !important;
}
.menu-user-email {
  color: #6b7280 !important;
  font-weight: 500 !important;
  font-size: 0.85rem !important;
}
.menu-item {
  transition: all 0.2s ease !important;
}
.menu-item :deep(.v-list-item-prepend) .v-icon { /* Style MDI icons in user menu */
  margin-inline-end: 16px !important;
  opacity: 0.7;
}
.menu-item:hover {
  background-color: #f8fafc !important; /* Vuetify's hover might be sufficient */
}
.item-content { /* Container for title and subtitle in user menu items */
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}
.item-title {
  font-weight: 500 !important; /* Adjusted from 600 */
  font-size: 0.9rem !important; /* Adjusted from 0.95 */
  line-height: 1.4;
}
.item-desc {
  font-size: 0.8rem !important;
  color: #6b7280 !important;
  font-weight: 400 !important;
  line-height: 1.3;
}
.logout-item.menu-item:hover {
  background-color: #fef2f2 !important;
}
.logout-item.menu-item:hover :deep(.v-list-item-prepend) .v-icon,
.logout-item.menu-item:hover .item-title {
  color: #dc2626 !important;
}
.logout-item.menu-item :deep(.v-list-item-prepend) .v-icon {
  color: #ef4444 !important; /* Slightly less intense red for default */
}

/* 移动端导航抽屉 */
.mobile-nav-drawer {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
}
.mobile-user-header {
  background: rgba(255,255,255,0.1);
  margin-bottom: 1rem;
  border-radius: 0 0 1rem 1rem; /* Optional: if you want rounded bottom */
}
.mobile-user-header .username {
  font-size: 1.1rem !important;
}

.mobile-nav-item {
  color: rgba(255,255,255,0.9) !important;
  margin: 0.25rem 0.5rem !important; /* Vuetify: my-1 mx-2 */
  border-radius: 8px !important;
  transition: all 0.3s ease !important;
  display: flex !important; /* 确保是flex布局 */
  align-items: center !important; /* 垂直居中对齐 */
  flex-direction: row !important; /* 水平排列 */
}
.mobile-nav-item:hover,
.mobile-nav-item.active {
  background: rgba(255,255,255,0.15) !important;
  color: white !important;
}
.mobile-nav-item .nav-icon { /* Emoji icons in mobile nav */
   margin-right: 16px; /* Vuetify v-list-item typically handles icon spacing */
}
.mobile-nav-icon-svg { /* SVG icons in mobile nav */
  filter: drop-shadow(0 1px 2px rgba(0,0,0,0.2));
  transition: all 0.3s ease;
  margin-right: 16px !important; /* 确保SVG图标和文字之间有间距 */
  width: 24px !important; /* 设置固定宽度，与MDI图标保持一致 */
  height: 24px !important; /* 设置固定高度，与MDI图标保持一致 */
}

/* 确保移动端所有图标（MDI和SVG）的间距一致 */
.mobile-nav-item :deep(.v-list-item__prepend) {
  width: 40px !important; /* 固定前置图标区域宽度 */
  display: flex !important; /* 确保图标容器是flex */
  align-items: center !important; /* 图标垂直居中 */
  justify-content: flex-start !important; /* 图标左对齐 */
  flex-shrink: 0 !important; /* 防止图标区域收缩 */
}

.mobile-nav-item :deep(.v-list-item__prepend) .v-icon {
  margin-inline-end: 16px !important; /* MDI图标右边距 */
  width: 24px !important; /* 设置MDI图标固定宽度 */
  height: 24px !important; /* 设置MDI图标固定高度 */
}

.mobile-nav-item :deep(.v-list-item__content) {
  display: flex !important; /* 确保内容区域是flex */
  align-items: center !important; /* 文字垂直居中 */
  flex: 1 !important; /* 占据剩余空间 */
}

.mobile-nav-sub-item { /* VIP sub-items in mobile */
  margin-left: 1rem !important; /* Indent sub-items */
  background: rgba(255,255,255,0.05) !important; /* Slightly different background for sub-items */
}
.mobile-nav-item.admin-item { /* Mobile admin item styling */
  background: linear-gradient(45deg, #ff6b6b, #ee5a52) !important;
  color: white !important;
}
.mobile-nav-item.admin-item:hover,
.mobile-nav-item.admin-item.active {
  background: linear-gradient(45deg, #ff5252, #e53935) !important;
}


/* 响应式 CSS for edge cases if Vuetify classes aren't enough */
/* Most responsive logic should be handled by Vuetify's display classes now */

/* 高对比度模式支持 (Consider if Vuetify handles this by default) */
@media (prefers-contrast: high) {
  .navigation-bar {
    background: #000 !important; /* Or system color */
    border-bottom: 2px solid ButtonText; /* Or system color */
  }
  /* ... other high contrast adjustments */
}

/* 减少动画效果 */
@media (prefers-reduced-motion: reduce) {
  .nav-item,
  .dropdown-arrow,
  .menu-arrow,
  .mobile-menu-toggle,
  .hamburger-line,
  .brand-icon-btn,
  .user-section,
  .dropdown-item,
  .menu-item,
  .mobile-nav-item {
    transition: none !important;
  }
}

/* 深色模式特定覆盖 (If Vuetify theme needs overrides) */
/* Example:
.theme--dark .dropdown-menu { background-color: #1E1E1E; }
*/
/* Most dark theme aspects should be handled by Vuetify's theme system. */
/* Your original CSS for prefers-color-scheme: dark might be for non-Vuetify parts or fine-tuning */
/* With useTheme, Vuetify applies .v-theme--dark class, so you can target that if needed. */
.v-theme--dark .dropdown-menu,
.v-theme--dark .user-menu {
  background: #2c313a !important; /* Example dark color */
  border-color: #404652 !important;
}
.v-theme--dark .dropdown-item,
.v-theme--dark .menu-item {
  color: #c9d1d9 !important;
}
.v-theme--dark .dropdown-item:hover,
.v-theme--dark .menu-item:hover {
  background: #373e47 !important;
}
.v-theme--dark .logout-item.menu-item:hover {
  background: #5e2525 !important;
}
.v-theme--dark .logout-item.menu-item:hover :deep(.v-list-item-prepend) .v-icon,
.v-theme--dark .logout-item.menu-item:hover .item-title {
  color: #ff8989 !important;
}
.v-theme--dark .logout-item.menu-item :deep(.v-list-item-prepend) .v-icon {
  color: #ff6b6b !important;
}

.v-theme--dark .menu-username { color: #e0e6f1 !important; }
.v-theme--dark .menu-user-email { color: #98a3b5 !important; }
.v-theme--dark .item-desc { color: #8892a3 !important; }


/* Focus styles - Vuetify usually provides good defaults, customize if needed */
.nav-item:focus-visible, /* Use focus-visible for accessibility */
.user-section:focus-visible,
.menu-item:focus-visible,
.brand-icon-btn:focus-visible,
.mobile-menu-toggle:focus-visible {
  outline: 2px solid rgba(255, 255, 255, 0.8) !important;
  outline-offset: 2px !important;
  box-shadow: 0 0 0 4px rgba(96, 165, 250, 0.5); /* Example focus ring */
}

.v-theme--dark .nav-item:focus-visible,
.v-theme--dark .user-section:focus-visible,
.v-theme--dark .brand-icon-btn:focus-visible,
.v-theme--dark .mobile-menu-toggle:focus-visible {
  outline-color: rgba(255, 255, 255, 0.9) !important;
  box-shadow: 0 0 0 4px rgba(127, 179, 255, 0.6);
}
</style>
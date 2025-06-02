<template>
  <div class="index-page-wrapper">
    <!-- 使用新的导航栏组件 -->
    <NavigationBar 
      :current-view="currentView" 
      @navigate="handleNavigate" 
    />
    
    <!-- Vuetify主内容区域 -->
    <v-main>
      <!-- 动态组件切换 -->
      <transition name="fade" mode="out-in">
        <component 
          :is="currentComponent" 
          :key="currentView"
          @back-to-home="handleNavigate('home')"
        />
      </transition>
    </v-main>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed, defineAsyncComponent } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'vue-toastification'
import NavigationBar from '@/components/layout/NavigationBar.vue'

// 异步加载组件
const QuizHomePage = defineAsyncComponent(() => import('../quiz/QuizHomePage.vue'))
const UsageStatsPage = defineAsyncComponent(() => import('../stats/UsageStatsPage.vue'))
const VipStatsPage = defineAsyncComponent(() => import('../vip/VipStatsPage.vue'))
const VipExportPage = defineAsyncComponent(() => import('../vip/VipExportPage.vue'))
const VipCollectionsPage = defineAsyncComponent(() => import('../vip/VipCollectionsPage.vue'))
const SystemControl = defineAsyncComponent(() => import('../admin/SystemControl.vue'))

const router = useRouter()
const toast = useToast()

// 当前视图状态
const currentView = ref<string>('home')

// 视图标题映射
const viewTitles: Record<string, string> = {
  home: '题目练习',
  stats: '使用统计',
  'vip-stats': 'VIP学习统计',
  'vip-export': 'VIP错题导出',
  'vip-collections': 'VIP错题集管理',
  admin: '系统管理'
}

// 组件映射
const components = {
  home: QuizHomePage,
  stats: UsageStatsPage,
  'vip-stats': VipStatsPage,
  'vip-export': VipExportPage,
  'vip-collections': VipCollectionsPage,
  admin: SystemControl
}

// 当前组件
const currentComponent = computed(() => {
  return components[currentView.value as keyof typeof components] || QuizHomePage
})

// 导航处理
const handleNavigate = (view: string) => {
  if (view === currentView.value) {
    return // 已经在当前视图，无需切换
  }
  
  currentView.value = view
  
  // 显示切换提示
  const title = viewTitles[view] || '未知页面'
  toast.success(`切换到${title} 🔄`, {
    timeout: 2000
  })
  
  // 滚动到顶部
  window.scrollTo({ top: 0, behavior: 'smooth' })
}
</script>

<style scoped>
.index-page-wrapper {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  width: 100vw;
  height: 100vh;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  overflow-y: auto;
  overflow-x: hidden;
}

/* 页面切换动画 */
.fade-enter-active,
.fade-leave-active {
  transition: all 0.3s ease;
}

.fade-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.fade-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

.fade-enter-to,
.fade-leave-from {
  opacity: 1;
  transform: translateX(0);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .index-page-wrapper {
    /* 移动端优化 */
  }
}
</style>

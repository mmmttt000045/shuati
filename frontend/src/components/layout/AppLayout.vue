<template>
  <div class="app-layout">
    <!-- 全局导航栏 -->
    <NavigationBar />
    
    <!-- 主内容区域 -->
    <v-main>
      <router-view />
    </v-main>
  </div>
</template>

<script setup lang="ts">
import NavigationBar from '@/components/layout/NavigationBar.vue'
</script>

<style scoped>
.app-layout {
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

/* 响应式设计 */
@media (max-width: 768px) {
  .app-layout {
    /* 移动端优化 */
  }
}
</style> 
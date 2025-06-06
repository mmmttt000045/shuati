<template>
  <div class="index-page-wrapper">
    <!-- 直接显示题库选择页面 -->
    <QuizHomePage />
  </div>
</template>

<script lang="ts" setup>
import QuizHomePage from '@/components/quiz/QuizHomePage.vue'
</script>

<style scoped>
.index-page-wrapper {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  overflow-y: auto;
  overflow-x: hidden;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .index-page-wrapper {
    /* 移动端优化 */
  }
}
</style>

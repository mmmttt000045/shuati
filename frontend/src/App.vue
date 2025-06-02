<script setup lang="ts">
import { RouterView } from 'vue-router';
import { computed } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();

// 动态计算是否为认证页面
const isAuthPage = computed(() => {
  return route.name === 'login' || route.name === 'register';
});
</script>

<template>
  <v-app>
    <div id="app" :class="{ 'auth-page': isAuthPage }">
      <RouterView />
    </div>
  </v-app>
</template>

<style>
/* 只保留最基本的全局样式，其他交给main.css处理 */
* {
  box-sizing: border-box;
}

html,
body {
  margin: 0;
  padding: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial,
    'Noto Sans', sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol',
    'Noto Color Emoji';
  overflow-x: hidden; /* 防止水平滚动条 */
}

/* 让main.css和页面组件完全接管#app的样式 */
#app {
  position: relative;
  /* 移除所有可能干扰全屏布局的样式 */
}

/* 认证页面特殊处理 */
#app.auth-page {
  width: 100vw;
  min-height: 100vh;
}

/* Vuetify 覆盖样式 */
.v-application {
  line-height: normal !important;
}

/* 确保导航栏在正确的层级 */
.v-app-bar {
  z-index: 1000 !important;
}

/* 移动端导航抽屉层级 */
.v-navigation-drawer {
  z-index: 1100 !important;
}
</style>
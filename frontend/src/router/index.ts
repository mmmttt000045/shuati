import { createRouter, createWebHistory } from 'vue-router';
import type { RouteRecordRaw } from 'vue-router';
import IndexPage from '@/components/layout/IndexPage.vue';
import PracticePage from '@/components/quiz/PracticePage.vue';
import CompletedPage from '@/components/quiz/CompletedPage.vue';
import LoginPage from '@/components/auth/LoginPage.vue';
import RegisterPage from '@/components/auth/RegisterPage.vue';
import NotFoundPage from '@/components/common/NotFoundPage.vue';
import SystemControl from '@/components/admin/SystemControl.vue';
import VipStatsPage from '@/components/vip/VipStatsPage.vue';
import VipExportPage from '@/components/vip/VipExportPage.vue';
import VipCollectionsPage from '@/components/vip/VipCollectionsPage.vue';
import EnhancedUsageStatsPage from '@/components/stats/EnhancedUsageStatsPage.vue';
import { useAuthStore } from '@/stores/auth';
import { USER_MODEL } from '@/types';

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: LoginPage,
    meta: {
      title: '登录',
      requiresAuth: false
    }
  },
  {
    path: '/register',
    name: 'register',
    component: RegisterPage,
    meta: {
      title: '注册',
      requiresAuth: false
    }
  },
  {
    path: '/',
    name: 'index',
    component: IndexPage,
    meta: {
      title: '题库选择',
      requiresAuth: true
    }
  },
  {
    path: '/practice',
    name: 'practice',
    component: PracticePage,
    props: (route) => ({
      tikuid: route.query.tikuid as string,
      order: route.query.order as string
    }),
    meta: {
      title: '在线练习',
      requiresAuth: true
    },
    beforeEnter: (to, from, next) => {
      // Check if required query parameters are present
      if (!to.query.tikuid) {
        next({ name: 'index' });
      } else {
        next();
      }
    }
  },
  {
    path: '/completed',
    name: 'completed',
    component: CompletedPage,
    meta: {
      title: '练习完成',
      requiresAuth: true
    }
  },
  // 管理员系统控制页面
  {
    path: '/admin',
    name: 'admin',
    component: SystemControl,
    meta: {
      title: '系统管理',
      requiresAuth: true,
      requiresAdmin: true
    }
  },
  // VIP功能页面路由
  {
    path: '/vip/stats',
    name: 'vip-stats',
    component: VipStatsPage,
    meta: {
      title: '学习统计',
      requiresAuth: true,
      requiresVip: true
    }
  },
  {
    path: '/vip/export',
    name: 'vip-export',
    component: VipExportPage,
    meta: {
      title: '错题导出',
      requiresAuth: true,
      requiresVip: true
    }
  },
  {
    path: '/vip/collections',
    name: 'vip-collections',
    component: VipCollectionsPage,
    meta: {
      title: '错题集管理',
      requiresAuth: true,
      requiresVip: true
    }
  },
  // 使用统计页面路由
  {
    path: '/admin/usage-stats',
    name: 'admin-usage-stats',
    component: EnhancedUsageStatsPage,
    meta: {
      title: '使用统计',
      requiresAuth: true,
      requiresAdmin: true
    }
  },
  // 用户资料和设置页面 (暂时重定向到主页)
  {
    path: '/profile',
    name: 'profile',
    component: IndexPage, // 临时使用 IndexPage，后续替换为 ProfilePage
    meta: {
      title: '个人资料',
      requiresAuth: true
    }
  },
  {
    path: '/settings',
    name: 'settings',
    component: IndexPage, // 临时使用 IndexPage，后续替换为 SettingsPage
    meta: {
      title: '设置',
      requiresAuth: true
    }
  },
  {
    path: '/404',
    name: 'notFound',
    component: NotFoundPage,
    meta: {
      title: '页面未找到',
      requiresAuth: false
    }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'catchAll',
    component: NotFoundPage,
    meta: {
      title: '页面未找到',
      requiresAuth: false
    }
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore();
  
  // Set page title
  document.title = `${to.meta.title || '在线练习'} - MT题库练习系统`;
  
  // Check if route requires authentication
  if (to.meta.requiresAuth !== false) {
    // Check if user is authenticated
    if (!authStore.isAuthenticated) {
      // Try to check auth status from server
      await authStore.checkAuth();
      
      // If still not authenticated, redirect to login
      if (!authStore.isAuthenticated) {
        next({ name: 'login' });
        return;
      }
    }
    
    // Check VIP permission
    if (to.meta.requiresVip) {
      const userModel = authStore.user?.model;
      if (userModel !== USER_MODEL.VIP && userModel !== USER_MODEL.ROOT) {
        // 可以显示提示消息或重定向到升级页面
        next({ name: 'index' });
        return;
      }
    }
    
    // Check admin permission
    if (to.meta.requiresAdmin) {
      const userModel = authStore.user?.model;
      if (userModel !== USER_MODEL.ROOT) {
        next({ name: 'index' });
        return;
      }
    }
  } else {
    // If user is already authenticated and trying to access login/register, redirect to home
    if (authStore.isAuthenticated && (to.name === 'login' || to.name === 'register')) {
      next({ name: 'index' });
      return;
    }
  }
  
  next();
});

export default router;

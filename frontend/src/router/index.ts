import { createRouter, createWebHistory } from 'vue-router';
import type { RouteRecordRaw } from 'vue-router';
import IndexPage from '@/components/IndexPage.vue';
import PracticePage from '@/components/PracticePage.vue';
import CompletedPage from '@/components/CompletedPage.vue';
import LoginPage from '@/components/LoginPage.vue';
import RegisterPage from '@/components/RegisterPage.vue';
import { useAuthStore } from '@/stores/auth';

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
      subject: route.query.subject as string,
      fileName: route.query.file as string,
      order: route.query.order as string
    }),
    meta: {
      title: '在线练习',
      requiresAuth: true
    },
    beforeEnter: (to, from, next) => {
      // Check if required query parameters are present
      if (!to.query.subject || !to.query.file) {
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
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
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

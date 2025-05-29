import { createRouter, createWebHistory } from 'vue-router';
import type { RouteRecordRaw } from 'vue-router';
import IndexPage from '@/components/IndexPage.vue';
import PracticePage from '@/components/PracticePage.vue';
import CompletedPage from '@/components/CompletedPage.vue';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'index',
    component: IndexPage,
    meta: {
      title: '题库选择'
    }
  },
  {
    path: '/practice',
    name: 'practice',
    component: PracticePage,
    props: (route) => ({
      subject: route.query.subject as string,
      fileName: route.query.file as string
    }),
    meta: {
      title: '在线练习'
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
      title: '练习完成'
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

router.beforeEach((to, _from, next) => {
  document.title = `${to.meta.title || '在线练习'} - MT题库练习系统`;
  next();
});

export default router;

import { createRouter, createWebHistory, type RouteRecordRaw, type RouteLocationNormalized } from 'vue-router';
import IndexPage from '../components/IndexPage.vue';
// We will create PracticePage.vue later
import PracticePage from '../components/PracticePage.vue';
import CompletedPage from '../components/CompletedPage.vue';

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    name: 'IndexPage',
    component: IndexPage,
  },
  {
    path: '/practice',
    name: 'PracticePage',
    component: PracticePage,
    props: (route: RouteLocationNormalized) => ({ file: route.query.file }) // Pass file query param as prop
  },
  {
    path: '/completed',
    name: 'CompletedPage',
    component: CompletedPage,
    props: (route: RouteLocationNormalized) => ({ file: route.query.file }) // Pass file query param as prop
  },
  // Add other routes for completed pages later
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
});

export default router;

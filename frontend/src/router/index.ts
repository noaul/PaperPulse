import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/dashboard',
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { title: '仪表盘' },
  },
  {
    path: '/feeds',
    name: 'Feeds',
    component: () => import('@/views/Feeds.vue'),
    meta: { title: '订阅源' },
  },
  {
    path: '/papers',
    name: 'Papers',
    component: () => import('@/views/Papers.vue'),
    meta: { title: '论文' },
  },
  {
    path: '/keywords',
    name: 'Keywords',
    component: () => import('@/views/Keywords.vue'),
    meta: { title: '关键词' },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/Settings.vue'),
    meta: { title: '设置' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  const title = to.meta.title ? `${to.meta.title} - PaperPulse` : 'PaperPulse'
  document.title = title as string
  next()
})

export default router

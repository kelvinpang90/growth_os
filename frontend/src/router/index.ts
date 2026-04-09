import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/phase2',
      name: 'phase2',
      component: () => import('@/views/Phase2View.vue'),
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('@/views/ProfileView.vue'),
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
    },
  ],
})

// 不需要登录的公开路由
const PUBLIC_ROUTES = ['/login', '/register']

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('access_token')
  if (!PUBLIC_ROUTES.includes(to.path) && !token) {
    // 未登录，跳转到登录页，并记录原始目标路径
    next({ path: '/login', query: { redirect: to.fullPath } })
  } else {
    next()
  }
})

export default router

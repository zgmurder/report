import { createRouter, createWebHistory } from 'vue-router'
import WorkbenchLayout from '@/layouts/WorkbenchLayout.vue'
import { useUserStore } from '@/stores/user'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/home/reports' },
    { path: '/login', component: () => import('@/views/LoginView.vue'), meta: { public: true } },
    {
      path: '/home',
      component: WorkbenchLayout,
      redirect: '/home/reports',
      children: [
        { path: 'reports', component: () => import('@/views/HomeView.vue') },
        { path: 'editor/:id', component: () => import('@/views/EditorView.vue') },
        { path: 'templates', component: () => import('@/views/TemplateView.vue') },
        { path: 'components', component: () => import('@/views/ComponentView.vue') },
        { path: 'data-sources', component: () => import('@/views/DataSourceView.vue') },
        { path: 'police', component: () => import('@/views/PoliceQueryView.vue') },
        { path: 'analysis', component: () => import('@/views/AnalysisView.vue') },
        { path: 'tags', component: () => import('@/views/PlaceholderView.vue'), meta: { title: '研判包' } },
        { path: 'warnings', component: () => import('@/views/PlaceholderView.vue'), meta: { title: '预警' } },
        { path: 'alarm-tagging', component: () => import('@/views/PlaceholderView.vue'), meta: { title: '警情打标' } },
        { path: 'folders', component: () => import('@/views/FolderView.vue') },
      ],
    },
    { path: '/editor/:id', redirect: (to) => `/home/editor/${to.params.id}` },
  ],
})

router.beforeEach(async (to) => {
  const userStore = useUserStore()
  if (to.meta.public) {
    if (to.path === '/login' && userStore.isLoggedIn) return '/home/reports'
    return true
  }
  if (!userStore.isLoggedIn) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (!userStore.user) {
    try {
      await userStore.loadCurrentUser()
    } catch {
      userStore.logout()
      return { path: '/login', query: { redirect: to.fullPath } }
    }
  }
  return true
})

export default router

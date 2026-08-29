import { createRouter, createWebHistory } from 'vue-router'
import WorkbenchLayout from '@/layouts/WorkbenchLayout.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/home/reports' },
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

export default router

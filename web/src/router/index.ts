import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('@/layout/index.vue'),
    children: [
      {
        path: '',
        redirect: '/projects',
      },
      {
        path: '/projects',
        name: 'ProjectList',
        component: () => import('@/views/project/List.vue'),
      },
      {
        path: '/projects/:id',
        name: 'ProjectDetail',
        component: () => import('@/views/project/Detail.vue'),
      },
      {
        path: '/materials',
        name: 'MaterialList',
        component: () => import('@/views/material/List.vue'),
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router

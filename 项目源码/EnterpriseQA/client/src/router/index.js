/**
 * Vue Router路由配置
 * 定义页面路由和导航守卫（权限控制）
 */
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { title: '登录' }
  },
  {
    path: '/',
    component: () => import('../views/Layout.vue'),
    redirect: '/chat',
    children: [
      {
        path: 'home',
        name: 'Home',
        component: () => import('../views/Home.vue'),
        meta: { title: '首页', requireAdmin: true }
      },
      {
        path: 'knowledge-base',
        name: 'KnowledgeBase',
        component: () => import('../views/KnowledgeBase.vue'),
        meta: { title: '知识库管理', requireAdmin: true }
      },
      {
        path: 'document',
        name: 'Document',
        component: () => import('../views/Document.vue'),
        meta: { title: '文档管理', requireAdmin: true }
      },
      {
        path: 'user-manage',
        name: 'UserManage',
        component: () => import('../views/UserManage.vue'),
        meta: { title: '用户管理', requireAdmin: true }
      },
      {
        path: 'chat',
        name: 'Chat',
        component: () => import('../views/Chat.vue'),
        meta: { title: '智能问答' }
      },
      {
        path: 'chat-history',
        name: 'ChatHistory',
        component: () => import('../views/ChatHistory.vue'),
        meta: { title: '对话历史' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 全局前置守卫：登录和权限检查
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  const userInfo = JSON.parse(localStorage.getItem('userInfo') || 'null')

  // 未登录且不是登录页，跳转登录
  if (!token && to.path !== '/login') {
    return next('/login')
  }

  // 已登录访问登录页，跳转首页
  if (token && to.path === '/login') {
    return next('/')
  }

  // 需要管理员权限的页面，普通用户无法访问
  if (to.meta.requireAdmin && userInfo?.role !== 'admin') {
    return next('/chat')
  }

  // 设置页面标题
  document.title = to.meta.title ? `${to.meta.title} - 企业知识库` : '企业知识库'
  next()
})

export default router

/**
 * 用户状态管理（Pinia）
 * 管理登录状态、用户信息和Token
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useUserStore = defineStore('user', () => {
  // 用户信息
  const userInfo = ref(JSON.parse(localStorage.getItem('userInfo') || 'null'))
  // Token
  const token = ref(localStorage.getItem('token') || '')

  /** 是否已登录 */
  const isLoggedIn = computed(() => !!token.value)

  /** 是否为管理员 */
  const isAdmin = computed(() => userInfo.value?.role === 'admin')

  /**
   * 设置登录信息
   * @param {Object} data - 包含token和user的对象
   */
  function setLoginInfo(data) {
    token.value = data.token
    userInfo.value = data.user
    localStorage.setItem('token', data.token)
    localStorage.setItem('userInfo', JSON.stringify(data.user))
  }

  /** 清除登录信息（退出登录） */
  function logout() {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('userInfo')
  }

  return { userInfo, token, isLoggedIn, isAdmin, setLoginInfo, logout }
})

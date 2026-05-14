/**
 * Axios实例配置
 * 设置baseURL、请求拦截器（自动携带Token）和响应拦截器（统一错误处理）
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'

// 创建axios实例
const request = axios.create({
  baseURL: '/api',
  timeout: 60000
})

// 请求拦截器：自动携带Token
request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器：统一处理错误
request.interceptors.response.use(
  (response) => {
    const res = response.data
    if (res.code === 200) {
      return res
    }
    // Token过期或未登录，跳转登录页
    if (res.code === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('userInfo')
      router.push('/login')
      ElMessage.error(res.message || '登录已过期')
      return Promise.reject(new Error(res.message))
    }
    ElMessage.error(res.message || '请求失败')
    return Promise.reject(new Error(res.message))
  },
  (error) => {
    ElMessage.error(error.message || '网络异常')
    return Promise.reject(error)
  }
)

export default request

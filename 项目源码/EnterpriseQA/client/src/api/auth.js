/**
 * 认证相关API
 */
import request from './index'

/** 用户登录 */
export function login(data) {
  return request.post('/auth/login', data)
}

/** 获取当前用户信息 */
export function getUserInfo() {
  return request.get('/auth/info')
}

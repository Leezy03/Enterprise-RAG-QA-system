/**
 * 用户管理API
 */
import request from './index'

/** 获取用户列表（分页） */
export function getUserList(params) {
  return request.get('/user/list', { params })
}

/** 新增用户 */
export function createUser(data) {
  return request.post('/user', data)
}

/** 编辑用户 */
export function updateUser(id, data) {
  return request.put(`/user/${id}`, data)
}

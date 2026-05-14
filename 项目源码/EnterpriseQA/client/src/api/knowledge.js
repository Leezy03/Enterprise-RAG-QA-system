/**
 * 知识库管理API
 */
import request from './index'

/** 获取知识库列表（分页） */
export function getKBList(params) {
  return request.get('/knowledge_base/list', { params })
}

/** 获取所有知识库（不分页） */
export function getAllKB() {
  return request.get('/knowledge_base/all')
}

/** 新增知识库 */
export function createKB(data) {
  return request.post('/knowledge_base', data)
}

/** 编辑知识库 */
export function updateKB(id, data) {
  return request.put(`/knowledge_base/${id}`, data)
}

/** 删除知识库 */
export function deleteKB(id) {
  return request.delete(`/knowledge_base/${id}`)
}

/**
 * 文档管理API
 */
import request from './index'

/** 获取文档列表（分页） */
export function getDocList(params) {
  return request.get('/document/list', { params })
}

/** 上传文档 */
export function uploadDoc(data) {
  return request.post('/document/upload', data, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000
  })
}

/** 删除文档 */
export function deleteDoc(id) {
  return request.delete(`/document/${id}`)
}

/** 重新向量化文档 */
export function revectorizeDoc(id) {
  return request.post(`/document/${id}/revectorize`, null, {
    timeout: 300000
  })
}

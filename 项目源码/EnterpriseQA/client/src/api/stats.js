/**
 * 统计数据API
 */
import request from './index'

/** 获取首页统计概览 */
export function getOverview() {
  return request.get('/stats/overview')
}

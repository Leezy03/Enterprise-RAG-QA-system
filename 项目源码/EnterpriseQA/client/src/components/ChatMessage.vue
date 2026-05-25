<template>
  <!-- 对话消息气泡组件 -->
  <div class="message-wrapper" :class="{ 'is-user': isUser }">
    <div class="avatar">
      <el-avatar :size="36" :icon="isUser ? UserFilled : Monitor" :style="avatarStyle" />
    </div>
    <div class="bubble" :class="{ 'user-bubble': isUser, 'ai-bubble': !isUser }">
      <div class="message-text">{{ message.content }}</div>
      <!-- AI回答时显示参考来源 -->
      <div v-if="!isUser && message.sources?.length" class="sources">
        <div class="sources-title">参考来源：</div>
        <el-tooltip
          v-for="(src, i) in message.sources"
          :key="i"
          :content="sourceTooltip(src)"
          placement="top"
        >
          <el-tag
          size="small"
          type="info"
          class="source-tag"
        >
            {{ sourceLabel(src) }}
          </el-tag>
        </el-tooltip>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 对话消息气泡组件
 * 区分用户消息和AI回答，AI回答可展示参考来源
 */
import { computed } from 'vue'
import { UserFilled, Monitor } from '@element-plus/icons-vue'

const props = defineProps({
  /** 消息对象 { role: 'user'|'ai', content: string, sources?: array } */
  message: { type: Object, required: true }
})

/** 是否为用户消息 */
const isUser = computed(() => props.message.role === 'user')

/** 头像样式 */
const avatarStyle = computed(() => ({
  backgroundColor: isUser.value ? '#409eff' : '#67c23a'
}))

/** 来源标签：优先使用后端生成的source_label，兜底兼容旧数据 */
function sourceLabel(src) {
  if (src.source_label) return src.source_label
  const fileName = src.file_name || '未知文档'
  const hasChunk = src.chunk_index !== null && src.chunk_index !== undefined
  const chunkIndex = Number(src.chunk_index)
  const chunk = hasChunk && Number.isInteger(chunkIndex) ? ` 第${chunkIndex + 1}段` : ''
  const sourceScore = typeof src.score === 'number'
    ? src.score
    : (typeof src.rerank_score === 'number' ? src.rerank_score : src.relevance_score)
  const score = typeof sourceScore === 'number'
    ? ` · 相关度${Math.round(sourceScore * 100)}%`
    : ''
  return `《${fileName}》${chunk}${score}`
}

/** 来源悬浮提示展示定位、检索信息和片段摘要 */
function sourceTooltip(src) {
  const lines = [sourceLabel(src)]
  if (src.source_location) lines.push(`位置：${src.source_location}`)
  if (src.retrieval_method) lines.push(`检索：${src.retrieval_method}`)
  if (typeof src.bm25_score === 'number') {
    lines.push(`BM25：${src.bm25_score.toFixed(4)}，命中词数：${src.bm25_matched_terms || 0}`)
  }
  if (src.bm25_matched_keywords) lines.push(`命中词：${src.bm25_matched_keywords}`)
  if (src.chunk_strategy) {
    lines.push(`切分：${src.chunk_strategy} ${src.chunk_size || '-'} / ${src.chunk_overlap || '-'}`)
  }
  const content = (src.content_preview || src.content || '').trim()
  if (content) lines.push(`片段：${content}`)
  return lines.join('\n')
}
</script>

<style scoped>
.message-wrapper {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  align-items: flex-start;
}

.message-wrapper.is-user {
  flex-direction: row-reverse;
}

.bubble {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.6;
  word-break: break-word;
  white-space: pre-wrap;
}

.user-bubble {
  background: #409eff;
  color: #fff;
  border-top-right-radius: 4px;
}

.ai-bubble {
  background: #f4f4f5;
  color: #303133;
  border-top-left-radius: 4px;
}

.message-text {
  font-size: 14px;
}

.sources {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid #e4e7ed;
}

.sources-title {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

.source-tag {
  margin-right: 4px;
  margin-bottom: 4px;
  max-width: 100%;
}

.source-tag :deep(.el-tag__content) {
  max-width: 420px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>

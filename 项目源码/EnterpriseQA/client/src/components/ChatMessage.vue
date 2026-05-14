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

/** 来源标签：文件名 + 片段序号 + 可选相似度 */
function sourceLabel(src) {
  const hasChunk = src.chunk_index !== null && src.chunk_index !== undefined
  const chunkIndex = Number(src.chunk_index)
  const chunk = hasChunk && Number.isInteger(chunkIndex) ? ` #${chunkIndex + 1}` : ''
  const sourceScore = typeof src.rerank_score === 'number' ? src.rerank_score : src.relevance_score
  const score = typeof sourceScore === 'number'
    ? ` ${Math.round(sourceScore * 100)}%`
    : ''
  return `${src.file_name}${chunk}${score}`
}

/** 来源悬浮提示展示片段摘要 */
function sourceTooltip(src) {
  return src.content || src.file_name || '参考片段'
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
}
</style>

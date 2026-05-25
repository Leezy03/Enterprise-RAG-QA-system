<template>
  <!-- 智能问答对话页面 -->
  <div class="chat-container">
    <!-- 左侧知识库选择 -->
    <div class="chat-sidebar">
      <div class="sidebar-title">选择知识库</div>
      <div class="kb-list">
        <div
          v-for="kb in kbList"
          :key="kb.id"
          class="kb-item"
          :class="{ active: selectedKb?.id === kb.id }"
          @click="selectKb(kb)"
        >
          <el-icon><FolderOpened /></el-icon>
          <span class="kb-name">{{ kb.kb_name }}</span>
          <el-tag size="small" type="info">{{ kb.doc_count }}篇</el-tag>
        </div>
      </div>
      <div v-if="kbList.length === 0" class="empty-tip">
        <el-empty description="暂无知识库" :image-size="60" />
      </div>
    </div>

    <!-- 右侧对话区域 -->
    <div class="chat-main">
      <!-- 对话窗口标题 -->
      <div class="chat-header">
        <span v-if="selectedKb">
          <el-icon><ChatDotRound /></el-icon>
          正在查询：{{ selectedKb.kb_name }}
        </span>
        <span v-else class="hint">请先从左侧选择一个知识库</span>
      </div>

      <!-- 消息列表 -->
      <div class="chat-messages" ref="messagesRef">
        <div v-if="messages.length === 0" class="welcome">
          <el-icon :size="64" color="#c0c4cc"><ChatDotSquare /></el-icon>
          <h3>欢迎使用企业知识库问答系统</h3>
          <p>请从左侧选择知识库，然后输入您的问题</p>
        </div>
        <template v-for="(msg, i) in messages" :key="i">
          <ChatMessage v-if="shouldShowMessage(msg)" :message="msg" />
        </template>
        <!-- 加载中提示 -->
        <div v-if="asking && !streamingStarted" class="loading-msg">
          <el-avatar :size="36" :icon="Monitor" style="background-color: #67c23a" />
          <div class="loading-bubble">
            <span class="loading-dot">思考中</span>
            <el-icon class="is-loading"><Loading /></el-icon>
          </div>
        </div>
      </div>

      <!-- 输入区域 -->
      <div class="chat-input">
        <el-input
          v-model="question"
          type="textarea"
          :rows="2"
          placeholder="请输入您的问题..."
          :disabled="!selectedKb || asking"
          @keydown.enter.exact.prevent="sendQuestion"
          resize="none"
        />
        <el-button
          type="primary"
          :icon="Promotion"
          :loading="asking"
          :disabled="!selectedKb || !question.trim()"
          @click="sendQuestion"
          class="send-btn"
        >
          发送
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 智能问答对话页面
 * 左侧选择知识库，右侧进行对话
 * 支持多轮对话，展示AI回答和参考来源
 */
import { ref, onMounted, nextTick } from 'vue'
import {
  ChatDotRound,
  ChatDotSquare,
  FolderOpened,
  Loading,
  Monitor,
  Promotion
} from '@element-plus/icons-vue'
import { getAllKB } from '../api/knowledge'
import { askQuestionStream } from '../api/chat'
import ChatMessage from '../components/ChatMessage.vue'

/** 知识库列表 */
const kbList = ref([])
/** 当前选中的知识库 */
const selectedKb = ref(null)
/** 对话消息列表 */
const messages = ref([])
/** 当前输入的问题 */
const question = ref('')
/** 是否正在请求中 */
const asking = ref(false)
/** 是否已经开始收到流式内容 */
const streamingStarted = ref(false)
/** 当前会话ID */
const sessionId = ref('')
/** 消息列表DOM引用 */
const messagesRef = ref(null)

/** 加载知识库列表 */
async function loadKBList() {
  try {
    const res = await getAllKB()
    kbList.value = res.data
  } catch (err) {
    // 错误已在拦截器处理
  }
}

/** 选择知识库 */
function selectKb(kb) {
  if (selectedKb.value?.id === kb.id) return
  selectedKb.value = kb
  messages.value = []
  sessionId.value = generateSessionId()
}

/** 生成会话ID */
function generateSessionId() {
  return 'sess_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
}

/** 自动滚动到底部 */
async function scrollToBottom() {
  await nextTick()
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

/** 更新AI消息，确保通过响应式数组触发页面刷新 */
function updateAiMessage(index, patch) {
  const current = messages.value[index]
  if (!current) return
  messages.value[index] = {
    ...current,
    ...patch
  }
}

/** 空的AI占位消息不渲染，避免和“思考中”提示同时出现 */
function shouldShowMessage(message) {
  return message.role === 'user' || Boolean(message.content) || Boolean(message.sources?.length)
}

/** 发送问题 */
async function sendQuestion() {
  const q = question.value.trim()
  if (!q || !selectedKb.value || asking.value) return

  // 添加用户消息
  messages.value.push({ role: 'user', content: q })
  question.value = ''
  asking.value = true
  streamingStarted.value = false
  scrollToBottom()

  try {
    messages.value.push({
      role: 'ai',
      content: '',
      sources: []
    })
    const aiMessageIndex = messages.value.length - 1

    await askQuestionStream({
      question: q,
      kb_id: selectedKb.value.id,
      session_id: sessionId.value
    }, {
      onMeta: (meta) => {
        if (meta.session_id) sessionId.value = meta.session_id
      },
      onChunk: (chunk) => {
        streamingStarted.value = true
        const currentContent = messages.value[aiMessageIndex]?.content || ''
        updateAiMessage(aiMessageIndex, { content: currentContent + chunk })
        scrollToBottom()
      },
      onDone: (data) => {
        const currentContent = messages.value[aiMessageIndex]?.content || ''
        updateAiMessage(aiMessageIndex, {
          content: currentContent || data.answer || '',
          sources: data.source_docs || []
        })
        if (data.session_id) sessionId.value = data.session_id
      },
      onError: (data) => {
        updateAiMessage(aiMessageIndex, {
          content: data.message || '抱歉，服务出现异常，请稍后重试。'
        })
      }
    })
  } catch (err) {
    const lastMessageIndex = messages.value.length - 1
    const lastMessage = messages.value[lastMessageIndex]
    if (lastMessage?.role === 'ai' && !lastMessage.content) {
      updateAiMessage(lastMessageIndex, {
        content: '抱歉，服务出现异常，请稍后重试。'
      })
    }
  } finally {
    asking.value = false
    streamingStarted.value = false
    scrollToBottom()
  }
}

onMounted(() => loadKBList())
</script>

<style scoped>
.chat-container {
  display: flex;
  height: calc(100vh - 100px);
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

/* 左侧知识库选择栏 */
.chat-sidebar {
  width: 260px;
  border-right: 1px solid #ebeef5;
  display: flex;
  flex-direction: column;
  background: #fafafa;
}

.sidebar-title {
  padding: 16px 20px;
  font-weight: 600;
  font-size: 15px;
  color: #303133;
  border-bottom: 1px solid #ebeef5;
}

.kb-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.kb-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
  margin-bottom: 4px;
}

.kb-item:hover {
  background: #ecf5ff;
}

.kb-item.active {
  background: #409eff;
  color: #fff;
}

.kb-item.active .el-tag {
  color: #fff;
  background: rgba(255, 255, 255, 0.2);
  border-color: transparent;
}

.kb-name {
  flex: 1;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-tip {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 右侧对话区域 */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.chat-header {
  padding: 14px 20px;
  border-bottom: 1px solid #ebeef5;
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 6px;
}

.chat-header .hint {
  color: #909399;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #c0c4cc;
  gap: 12px;
}

.welcome h3 {
  color: #909399;
  font-size: 18px;
}

.welcome p {
  font-size: 14px;
}

.loading-msg {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 20px;
}

.loading-bubble {
  background: #f4f4f5;
  padding: 12px 16px;
  border-radius: 12px;
  border-top-left-radius: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #909399;
  font-size: 14px;
}

/* 输入区域 */
.chat-input {
  padding: 16px 20px;
  border-top: 1px solid #ebeef5;
  display: flex;
  gap: 12px;
  align-items: flex-end;
  background: #fff;
}

.chat-input :deep(.el-textarea__inner) {
  border-radius: 8px;
}

.send-btn {
  height: 54px;
  border-radius: 8px;
}
</style>

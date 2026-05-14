/**
 * 问答对话API
 */
import request from './index'

/** 发送问题（RAG问答） */
export function askQuestion(data) {
  return request.post('/chat/ask', data, {
    timeout: 3600000
  })
}

/** 发送问题（RAG流式问答，基于fetch读取SSE） */
export async function askQuestionStream(data, handlers = {}) {
  const token = localStorage.getItem('token')
  const response = await fetch('/api/chat/ask_stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: JSON.stringify(data)
  })

  if (!response.ok || !response.body) {
    throw new Error(`流式问答请求失败: ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  function dispatchEvent(rawEvent) {
    const lines = rawEvent.split('\n')
    const eventLine = lines.find((line) => line.startsWith('event:'))
    const dataLines = lines.filter((line) => line.startsWith('data:'))

    if (!eventLine || dataLines.length === 0) return

    const eventName = eventLine.replace('event:', '').trim()
    const payloadText = dataLines
      .map((line) => line.replace('data:', '').trim())
      .join('\n')
    const payload = JSON.parse(payloadText)

    if (eventName === 'meta') handlers.onMeta?.(payload)
    if (eventName === 'chunk') handlers.onChunk?.(payload.content || '')
    if (eventName === 'done') handlers.onDone?.(payload)
    if (eventName === 'error') {
      handlers.onError?.(payload)
      throw new Error(payload.message || '流式问答异常')
    }
  }

  while (true) {
    const { value, done } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const events = buffer.split('\n\n')
    buffer = events.pop() || ''

    for (const event of events) {
      if (event.trim()) dispatchEvent(event)
    }
  }

  if (buffer.trim()) {
    dispatchEvent(buffer)
  }
}

/** 获取对话历史列表 */
export function getChatHistory(params) {
  return request.get('/chat/history', { params })
}

/** 获取指定会话的对话记录 */
export function getSessionChats(sessionId) {
  return request.get(`/chat/session/${sessionId}`)
}

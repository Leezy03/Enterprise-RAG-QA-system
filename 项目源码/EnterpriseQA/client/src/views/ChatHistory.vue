<template>
  <!-- 对话历史页面 -->
  <div class="page-container">
    <!-- 筛选栏 -->
    <el-card shadow="never">
      <el-row :gutter="16" align="middle">
        <el-col :span="8">
          <el-select
            v-model="queryParams.kb_id"
            placeholder="按知识库筛选"
            clearable
            @change="loadList"
            style="width: 100%"
          >
            <el-option
              v-for="kb in kbOptions"
              :key="kb.id"
              :label="kb.kb_name"
              :value="kb.id"
            />
          </el-select>
        </el-col>
      </el-row>
    </el-card>

    <!-- 历史记录表格 -->
    <el-card shadow="never">
      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="question" label="问题" min-width="250" show-overflow-tooltip />
        <el-table-column prop="answer" label="回答" min-width="300" show-overflow-tooltip />
        <el-table-column prop="kb_name" label="知识库" width="130" />
        <el-table-column prop="username" label="提问者" width="100" />
        <el-table-column prop="create_time" label="时间" width="170" />
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="showDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="queryParams.page"
          v-model:page-size="queryParams.page_size"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @change="loadList"
        />
      </div>
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailVisible" title="对话详情" width="650px">
      <div class="detail-content" v-if="currentChat">
        <div class="detail-item">
          <div class="detail-label">提问：</div>
          <div class="detail-value question">{{ currentChat.question }}</div>
        </div>
        <div class="detail-item">
          <div class="detail-label">回答：</div>
          <div class="detail-value answer">{{ currentChat.answer }}</div>
        </div>
        <div class="detail-item" v-if="currentChat.source_docs?.length">
          <div class="detail-label">参考来源：</div>
          <div class="detail-value">
            <el-tag
              v-for="(src, i) in currentChat.source_docs"
              :key="i"
              size="small"
              class="source-tag"
            >
              {{ src.file_name }}
            </el-tag>
          </div>
        </div>
        <div class="detail-item">
          <div class="detail-label">知识库：</div>
          <div class="detail-value">{{ currentChat.kb_name }}</div>
        </div>
        <div class="detail-item">
          <div class="detail-label">时间：</div>
          <div class="detail-value">{{ currentChat.create_time }}</div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 对话历史页面
 * 展示用户的历史问答记录，支持按知识库筛选和查看详情
 */
import { ref, reactive, onMounted } from 'vue'
import { getChatHistory } from '../api/chat'
import { getAllKB } from '../api/knowledge'

const loading = ref(false)
const detailVisible = ref(false)
const tableData = ref([])
const total = ref(0)
const kbOptions = ref([])
const currentChat = ref(null)

const queryParams = reactive({ page: 1, page_size: 10, kb_id: null })

async function loadKBOptions() {
  const res = await getAllKB()
  kbOptions.value = res.data
}

async function loadList() {
  loading.value = true
  try {
    const res = await getChatHistory(queryParams)
    tableData.value = res.data.list
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

function showDetail(row) {
  currentChat.value = row
  detailVisible.value = true
}

onMounted(() => {
  loadKBOptions()
  loadList()
})
</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.detail-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-item {
  display: flex;
  gap: 8px;
}

.detail-label {
  font-weight: 600;
  color: #303133;
  white-space: nowrap;
  min-width: 70px;
}

.detail-value {
  color: #606266;
  line-height: 1.6;
  word-break: break-all;
}

.detail-value.question {
  color: #409eff;
  font-weight: 500;
}

.detail-value.answer {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 6px;
  white-space: pre-wrap;
}

.source-tag {
  margin-right: 6px;
  margin-bottom: 4px;
}
</style>

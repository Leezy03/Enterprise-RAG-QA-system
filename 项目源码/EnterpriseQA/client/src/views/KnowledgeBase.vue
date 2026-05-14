<template>
  <!-- 知识库管理页面 -->
  <div class="page-container">
    <!-- 操作栏 -->
    <el-card shadow="never" class="search-bar">
      <el-row :gutter="16" align="middle">
        <el-col :span="8">
          <el-input
            v-model="queryParams.keyword"
            placeholder="搜索知识库名称"
            clearable
            :prefix-icon="Search"
            @clear="loadList"
            @keyup.enter="loadList"
          />
        </el-col>
        <el-col :span="16" style="text-align: right">
          <el-button type="primary" :icon="Plus" @click="handleAdd">新增知识库</el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 数据表格 -->
    <el-card shadow="never" class="table-card">
      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="kb_name" label="知识库名称" min-width="150" />
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="doc_count" label="文档数" width="80" align="center" />
        <el-table-column prop="creator_name" label="创建者" width="100" />
        <el-table-column prop="create_time" label="创建时间" width="170" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="handleEdit(row)">编辑</el-button>
            <el-popconfirm title="确认删除该知识库？" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button type="danger" link>删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
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

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑知识库' : '新增知识库'"
      width="500px"
    >
      <el-form ref="formRef" :model="formData" :rules="rules" label-width="100px">
        <el-form-item label="知识库名称" prop="kb_name">
          <el-input v-model="formData.kb_name" placeholder="请输入知识库名称" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="3"
            placeholder="请输入知识库描述"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 知识库管理页面
 * 支持知识库的列表查询、新增、编辑和删除操作
 */
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Plus } from '@element-plus/icons-vue'
import { getKBList, createKB, updateKB, deleteKB } from '../api/knowledge'

const loading = ref(false)
const submitLoading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const tableData = ref([])
const total = ref(0)
const formRef = ref(null)

/** 查询参数 */
const queryParams = reactive({ page: 1, page_size: 10, keyword: '' })

/** 表单数据 */
const formData = reactive({ id: null, kb_name: '', description: '' })

/** 表单校验 */
const rules = {
  kb_name: [{ required: true, message: '请输入知识库名称', trigger: 'blur' }]
}

/** 加载知识库列表 */
async function loadList() {
  loading.value = true
  try {
    const res = await getKBList(queryParams)
    tableData.value = res.data.list
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

/** 打开新增对话框 */
function handleAdd() {
  isEdit.value = false
  Object.assign(formData, { id: null, kb_name: '', description: '' })
  dialogVisible.value = true
}

/** 打开编辑对话框 */
function handleEdit(row) {
  isEdit.value = true
  Object.assign(formData, { id: row.id, kb_name: row.kb_name, description: row.description })
  dialogVisible.value = true
}

/** 提交表单 */
async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitLoading.value = true
  try {
    if (isEdit.value) {
      await updateKB(formData.id, formData)
      ElMessage.success('更新成功')
    } else {
      await createKB(formData)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadList()
  } finally {
    submitLoading.value = false
  }
}

/** 删除知识库 */
async function handleDelete(id) {
  await deleteKB(id)
  ElMessage.success('删除成功')
  loadList()
}

onMounted(() => loadList())
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
</style>

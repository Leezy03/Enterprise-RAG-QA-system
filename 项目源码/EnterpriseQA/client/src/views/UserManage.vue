<template>
  <!-- 用户管理页面（仅管理员可见） -->
  <div class="page-container">
    <!-- 操作栏 -->
    <el-card shadow="never" class="search-bar">
      <el-row :gutter="16" align="middle">
        <el-col :span="8">
          <el-input
            v-model="queryParams.keyword"
            placeholder="搜索用户名或昵称"
            clearable
            :prefix-icon="Search"
            @clear="loadList"
            @keyup.enter="loadList"
          />
        </el-col>
        <el-col :span="16" style="text-align: right">
          <el-button type="primary" :icon="Plus" @click="handleAdd">新增用户</el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 数据表格 -->
    <el-card shadow="never">
      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="nickname" label="昵称" width="120" />
        <el-table-column prop="role" label="角色" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : 'primary'" size="small">
              {{ row.role === 'admin' ? '管理员' : '普通用户' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
              {{ row.status === 1 ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="create_time" label="创建时间" width="170" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="handleEdit(row)">编辑</el-button>
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

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑用户' : '新增用户'"
      width="500px"
    >
      <el-form ref="formRef" :model="formData" :rules="rules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="formData.username" :disabled="isEdit" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码" :prop="isEdit ? '' : 'password'">
          <el-input
            v-model="formData.password"
            type="password"
            :placeholder="isEdit ? '不修改请留空' : '请输入密码'"
            show-password
          />
        </el-form-item>
        <el-form-item label="昵称" prop="nickname">
          <el-input v-model="formData.nickname" placeholder="请输入昵称" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="formData.role" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="普通用户" value="user" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="isEdit" label="状态">
          <el-switch v-model="formData.status" :active-value="1" :inactive-value="0" />
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
 * 用户管理页面
 * 管理员可新增、编辑用户，设置角色和启用/禁用状态
 */
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Plus } from '@element-plus/icons-vue'
import { getUserList, createUser, updateUser } from '../api/user'

const loading = ref(false)
const submitLoading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const tableData = ref([])
const total = ref(0)
const formRef = ref(null)

const queryParams = reactive({ page: 1, page_size: 10, keyword: '' })

const formData = reactive({
  id: null, username: '', password: '', nickname: '', role: 'user', status: 1
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  nickname: [{ required: true, message: '请输入昵称', trigger: 'blur' }]
}

async function loadList() {
  loading.value = true
  try {
    const res = await getUserList(queryParams)
    tableData.value = res.data.list
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

function handleAdd() {
  isEdit.value = false
  Object.assign(formData, { id: null, username: '', password: '', nickname: '', role: 'user', status: 1 })
  dialogVisible.value = true
}

function handleEdit(row) {
  isEdit.value = true
  Object.assign(formData, { id: row.id, username: row.username, password: '', nickname: row.nickname, role: row.role, status: row.status })
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitLoading.value = true
  try {
    if (isEdit.value) {
      const updateData = { nickname: formData.nickname, role: formData.role, status: formData.status }
      if (formData.password) updateData.password = formData.password
      await updateUser(formData.id, updateData)
      ElMessage.success('更新成功')
    } else {
      await createUser(formData)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadList()
  } finally {
    submitLoading.value = false
  }
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

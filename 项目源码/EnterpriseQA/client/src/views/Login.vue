<template>
  <!-- 登录页面 -->
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <el-icon :size="40" color="#409eff"><ChatDotSquare /></el-icon>
        <h2>企业知识库问答系统</h2>
        <p class="subtitle">基于RAG的智能知识检索与问答平台</p>
      </div>
      <el-form
        ref="formRef"
        :model="loginForm"
        :rules="rules"
        class="login-form"
        @keyup.enter="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="请输入用户名"
            :prefix-icon="User"
            size="large"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            :prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            class="login-btn"
            :loading="loading"
            @click="handleLogin"
          >
            登 录
          </el-button>
        </el-form-item>
      </el-form>
      <div class="login-footer">
        <span>测试账号: admin / 123456（管理员） | user1 / 123456（普通用户）</span>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 登录页面
 * 支持用户名密码登录，登录成功后跳转至对应首页
 */
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { login } from '../api/auth'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref(null)
const loading = ref(false)

/** 登录表单 */
const loginForm = reactive({
  username: '',
  password: ''
})

/** 表单校验规则 */
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

/** 处理登录 */
async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const res = await login(loginForm)
    userStore.setLoginInfo(res.data)
    ElMessage.success('登录成功')
    // 管理员跳转数据概览，普通用户跳转智能问答
    if (res.data.user.role === 'admin') {
      router.push('/home')
    } else {
      router.push('/chat')
    }
  } catch (err) {
    // 错误已在拦截器中处理
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  width: 100%;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 420px;
  padding: 40px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}

.login-header {
  text-align: center;
  margin-bottom: 30px;
}

.login-header h2 {
  margin: 12px 0 8px;
  color: #303133;
  font-size: 22px;
}

.subtitle {
  color: #909399;
  font-size: 13px;
}

.login-btn {
  width: 100%;
}

.login-footer {
  text-align: center;
  margin-top: 16px;
  font-size: 12px;
  color: #c0c4cc;
}
</style>

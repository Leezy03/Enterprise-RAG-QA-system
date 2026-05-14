<template>
  <!-- 后台主布局：左侧菜单 + 顶栏 + 内容区 -->
  <el-container class="layout-container">
    <!-- 左侧菜单栏 -->
    <el-aside :width="isCollapse ? '64px' : '220px'" class="aside">
      <div class="logo">
        <el-icon :size="24"><ChatDotSquare /></el-icon>
        <span v-show="!isCollapse" class="logo-text">企业知识库</span>
      </div>
      <el-menu
        :default-active="$route.path"
        :collapse="isCollapse"
        :router="true"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409eff"
        class="aside-menu"
      >
        <!-- 管理员菜单 -->
        <template v-if="userStore.isAdmin">
          <el-menu-item index="/home">
            <el-icon><DataAnalysis /></el-icon>
            <template #title>数据概览</template>
          </el-menu-item>
          <el-menu-item index="/knowledge-base">
            <el-icon><FolderOpened /></el-icon>
            <template #title>知识库管理</template>
          </el-menu-item>
          <el-menu-item index="/document">
            <el-icon><Document /></el-icon>
            <template #title>文档管理</template>
          </el-menu-item>
          <el-menu-item index="/user-manage">
            <el-icon><User /></el-icon>
            <template #title>用户管理</template>
          </el-menu-item>
        </template>
        <!-- 通用菜单 -->
        <el-menu-item index="/chat">
          <el-icon><ChatDotRound /></el-icon>
          <template #title>智能问答</template>
        </el-menu-item>
        <el-menu-item index="/chat-history">
          <el-icon><Clock /></el-icon>
          <template #title>对话历史</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 右侧内容区 -->
    <el-container>
      <!-- 顶部栏 -->
      <el-header class="header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="isCollapse = !isCollapse">
            <Fold v-if="!isCollapse" />
            <Expand v-else />
          </el-icon>
          <span class="page-title">{{ $route.meta.title }}</span>
        </div>
        <div class="header-right">
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="32" :icon="UserFilled" />
              <span class="username">{{ userStore.userInfo?.nickname }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 主内容区 -->
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
/**
 * 后台布局组件
 * 包含侧边栏（根据角色动态显示菜单）、顶部栏和内容区
 */
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { UserFilled } from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()

/** 控制侧边栏折叠 */
const isCollapse = ref(false)

/** 处理下拉菜单命令 */
function handleCommand(command) {
  if (command === 'logout') {
    userStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.aside {
  background-color: #304156;
  transition: width 0.3s;
  overflow: hidden;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  gap: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.logo-text {
  font-size: 16px;
  font-weight: 600;
  white-space: nowrap;
}

.aside-menu {
  border-right: none;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #ebeef5;
  background: #fff;
  padding: 0 20px;
  height: 60px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.collapse-btn {
  font-size: 20px;
  cursor: pointer;
  color: #606266;
}

.page-title {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
}

.header-right .user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.username {
  font-size: 14px;
  color: #606266;
}

.main {
  background: #f0f2f5;
  padding: 20px;
  overflow-y: auto;
}
</style>

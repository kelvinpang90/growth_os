<template>
  <el-container class="layout">
    <el-aside width="220px" class="sidebar">
      <div class="logo">Growth OS</div>
      <el-menu :default-active="activeMenu" router>
        <el-menu-item index="/">
          <el-icon><House /></el-icon>
          <span>首页</span>
        </el-menu-item>
        <el-menu-item index="/phase1">
          <el-icon><Search /></el-icon>
          <span>选品发现</span>
        </el-menu-item>
        <el-menu-item index="/phase2">
          <el-icon><User /></el-icon>
          <span>达人管理</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <span class="title">控制台</span>
        <el-button type="danger" plain size="small" @click="logout">退出登录</el-button>
      </el-header>

      <el-main>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-card shadow="hover">
              <template #header>选品发现 Phase 1</template>
              <p>AI 驱动的跨境电商选品分析</p>
              <el-button type="primary" @click="$router.push('/phase1')">进入</el-button>
            </el-card>
          </el-col>
          <el-col :span="8">
            <el-card shadow="hover">
              <template #header>达人管理 Phase 2</template>
              <p>网红达人发现与触达</p>
              <el-button type="primary" @click="$router.push('/phase2')">进入</el-button>
            </el-card>
          </el-col>
          <el-col :span="8">
            <el-card shadow="hover">
              <template #header>API 文档</template>
              <p>查看后端接口文档</p>
              <el-button @click="openDocs">打开 Swagger</el-button>
            </el-card>
          </el-col>
        </el-row>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const activeMenu = computed(() => route.path)

function logout() {
  authStore.clearToken()
  router.push('/login')
}

function openDocs() {
  window.open('/docs', '_blank')
}
</script>

<style scoped>
.layout {
  height: 100vh;
}
.sidebar {
  background: #1e2a3a;
}
.logo {
  color: #fff;
  font-size: 18px;
  font-weight: bold;
  padding: 20px;
  text-align: center;
  border-bottom: 1px solid #2d3f53;
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #eee;
}
.title {
  font-size: 16px;
  font-weight: 600;
}
</style>

<template>
  <div class="page">
    <el-page-header @back="$router.push('/')" content="选品发现 Phase 1" />

    <el-row :gutter="16" style="margin-top: 20px">
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>热门关键词</template>
          <el-button type="primary" :loading="loadingKeywords" @click="fetchKeywords">
            刷新
          </el-button>
          <el-table :data="keywords" style="margin-top: 12px" stripe>
            <el-table-column prop="keyword" label="关键词" />
            <el-table-column prop="platform" label="平台" width="100" />
            <el-table-column prop="score" label="热度" width="80" />
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>AI 推荐产品</template>
          <el-button type="primary" :loading="loadingProducts" @click="fetchProducts">
            刷新
          </el-button>
          <el-table :data="products" style="margin-top: 12px" stripe>
            <el-table-column prop="name" label="产品名称" />
            <el-table-column prop="platform" label="平台" width="100" />
            <el-table-column prop="score" label="评分" width="80" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const keywords = ref<any[]>([])
const products = ref<any[]>([])
const loadingKeywords = ref(false)
const loadingProducts = ref(false)

async function fetchKeywords() {
  loadingKeywords.value = true
  try {
    const res = await axios.get('/api/phase1/trending-keywords')
    keywords.value = res.data
  } catch {
    ElMessage.error('获取关键词失败')
  } finally {
    loadingKeywords.value = false
  }
}

async function fetchProducts() {
  loadingProducts.value = true
  try {
    const res = await axios.get('/api/phase1/recommendations')
    products.value = res.data
  } catch {
    ElMessage.error('获取产品失败')
  } finally {
    loadingProducts.value = false
  }
}
</script>

<style scoped>
.page {
  padding: 20px;
}
</style>

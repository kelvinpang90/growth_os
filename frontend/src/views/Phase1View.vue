<template>
  <div class="page">
    <el-page-header @back="$router.push('/')" :content="$t('phase1.title')" />

    <el-row :gutter="16" style="margin-top: 20px">
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>{{ $t('phase1.trending_keywords') }}</template>
          <el-button type="primary" :loading="loadingKeywords" @click="fetchKeywords">
            {{ $t('phase1.refresh') }}
          </el-button>
          <el-table :data="keywords" style="margin-top: 12px" stripe>
            <el-table-column prop="keyword" :label="$t('col.keyword')" />
            <el-table-column prop="platform" :label="$t('col.platform')" width="100" />
            <el-table-column prop="score" :label="$t('col.score')" width="80" />
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>{{ $t('phase1.recommended_products') }}</template>
          <el-button type="primary" :loading="loadingProducts" @click="fetchProducts">
            {{ $t('phase1.refresh') }}
          </el-button>
          <el-table :data="products" style="margin-top: 12px" stripe>
            <el-table-column prop="title" :label="$t('col.product_name')" />
            <el-table-column prop="platform" :label="$t('col.platform')" width="100" />
            <el-table-column prop="score" :label="$t('col.ai_score')" width="80" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const { t } = useI18n()

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
    ElMessage.error(t('phase1.error_keywords'))
  } finally {
    loadingKeywords.value = false
  }
}

async function fetchProducts() {
  loadingProducts.value = true
  try {
    const res = await axios.get('/api/phase1/recommendations')
    products.value = res.data.data ?? []
  } catch {
    ElMessage.error(t('phase1.error_products'))
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

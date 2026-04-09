<template>
  <el-container class="layout">
    <el-aside width="220px" class="sidebar">
      <div class="logo">Growth OS</div>
      <el-menu :default-active="activeMenu" router>
        <el-menu-item index="/">
          <el-icon><House /></el-icon>
          <span>{{ $t('nav.home') }}</span>
        </el-menu-item>
        <el-menu-item index="/phase2">
          <el-icon><User /></el-icon>
          <span>{{ $t('nav.influencer') }}</span>
        </el-menu-item>
        <el-menu-item index="/profile">
          <el-icon><UserFilled /></el-icon>
          <span>{{ $t('nav.profile') }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <span class="title">{{ $t('nav.console') }}</span>
        <el-button type="danger" plain size="small" @click="logout">{{ $t('nav.logout') }}</el-button>
      </el-header>

      <el-main class="main-content">

        <!-- AI 推荐产品 -->
        <el-card shadow="never" class="data-card">
          <template #header>
            <span>{{ $t('home.recommended_products') }}</span>
            <span class="header-sub">{{ $t('home.last_n_days') }}</span>
          </template>
          <el-table
            v-loading="loadingProducts"
            :data="pagedProducts"
            stripe
            style="width: 100%"
          >
            <el-table-column prop="title" :label="$t('col.product_name')" min-width="200" show-overflow-tooltip />
            <el-table-column prop="platform" :label="$t('col.platform')" width="90" />
            <el-table-column prop="category" :label="$t('col.category')" width="110" show-overflow-tooltip />
            <el-table-column prop="price" :label="$t('col.price')" width="80" />
            <el-table-column prop="ai_score" :label="$t('col.ai_score')" width="90" sortable />
            <el-table-column prop="profit_rate" :label="$t('col.profit_rate')" width="100" sortable />
            <el-table-column prop="competition" :label="$t('col.competition')" width="90" />
          </el-table>
          <div class="pagination-bar">
            <el-pagination
              v-model:current-page="productPage"
              :page-size="pageSize"
              :total="products.length"
              layout="prev, pager, next, total"
              background
              small
            />
          </div>
          <el-empty v-if="!loadingProducts && products.length === 0" :description="$t('home.no_recommendations')" />
        </el-card>

        <!-- 热门关键词 -->
        <el-card shadow="never" class="data-card">
          <template #header>{{ $t('home.trending_keywords') }}</template>
          <el-table
            v-loading="loadingKeywords"
            :data="pagedKeywords"
            stripe
            style="width: 100%"
          >
            <el-table-column prop="keyword" :label="$t('col.keyword')" min-width="180" />
            <el-table-column prop="platform" :label="$t('col.platform')" width="90" />
            <el-table-column prop="volume" :label="$t('col.volume')" width="100" sortable />
            <el-table-column prop="trend" :label="$t('col.trend')" width="100" />
            <el-table-column prop="region" :label="$t('col.region')" width="90" />
          </el-table>
          <div class="pagination-bar">
            <el-pagination
              v-model:current-page="keywordPage"
              :page-size="pageSize"
              :total="keywords.length"
              layout="prev, pager, next, total"
              background
              small
            />
          </div>
          <el-empty v-if="!loadingKeywords && keywords.length === 0" :description="$t('home.no_keywords')" />
        </el-card>

      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const { t } = useI18n()

const activeMenu = computed(() => route.path)

const products = ref<any[]>([])
const keywords = ref<any[]>([])
const loadingProducts = ref(false)
const loadingKeywords = ref(false)

const pageSize = 10
const productPage = ref(1)
const keywordPage = ref(1)

const pagedProducts = computed(() => {
  const start = (productPage.value - 1) * pageSize
  return products.value.slice(start, start + pageSize)
})

const pagedKeywords = computed(() => {
  const start = (keywordPage.value - 1) * pageSize
  return keywords.value.slice(start, start + pageSize)
})

async function fetchProducts() {
  loadingProducts.value = true
  try {
    const res = await axios.get('/api/phase1/recommendations', {
      params: { days: 1, limit: 200 },
    })
    products.value = res.data.data ?? []
  } catch {
    ElMessage.error(t('home.error_products'))
  } finally {
    loadingProducts.value = false
  }
}

async function fetchKeywords() {
  loadingKeywords.value = true
  try {
    const res = await axios.get('/api/phase1/trending-keywords', {
      params: { limit: 200 },
    })
    keywords.value = res.data.data ?? []
  } catch {
    ElMessage.error(t('home.error_keywords'))
  } finally {
    loadingKeywords.value = false
  }
}

function logout() {
  authStore.clearToken()
  router.push('/login')
}

onMounted(() => {
  fetchProducts()
  fetchKeywords()
})
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
.main-content {
  background: #f5f7fa;
  padding: 20px;
}
.data-card {
  margin-bottom: 20px;
}
.header-sub {
  font-size: 12px;
  color: #999;
  margin-left: 8px;
}
.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>

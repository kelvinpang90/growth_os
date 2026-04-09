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
        <span class="title">{{ $t('influencer.title') }}</span>
        <el-button type="danger" plain size="small" @click="logout">{{ $t('nav.logout') }}</el-button>
      </el-header>

      <el-main class="main-content">
        <el-card shadow="never">

          <!-- 筛选栏 -->
          <el-form :model="filter" inline class="filter-bar">
            <el-form-item :label="$t('influencer.filter_category')">
              <el-select
                v-model="filter.category"
                :placeholder="$t('influencer.all_categories')"
                clearable
                style="width: 140px"
              >
                <el-option v-for="cat in categories" :key="cat" :label="cat" :value="cat" />
              </el-select>
            </el-form-item>

            <el-form-item :label="$t('influencer.filter_status')">
              <el-select
                v-model="filter.status"
                :placeholder="$t('influencer.all_statuses')"
                clearable
                style="width: 130px"
              >
                <el-option
                  v-for="(label, val) in statusOptions"
                  :key="val"
                  :label="label"
                  :value="val"
                />
              </el-select>
            </el-form-item>

            <el-form-item :label="$t('influencer.filter_min_followers')">
              <el-input-number
                v-model="filter.min_followers"
                :min="0"
                :step="10000"
                style="width: 140px"
                controls-position="right"
              />
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="doSearch">{{ $t('influencer.search') }}</el-button>
              <el-button @click="resetFilter">{{ $t('influencer.reset') }}</el-button>
            </el-form-item>
          </el-form>

          <!-- 达人表格 -->
          <el-table
            v-loading="loading"
            :data="influencers"
            stripe
            style="width: 100%"
          >
            <el-table-column :label="$t('influencer.col.username')" min-width="160">
              <template #default="{ row }">
                <div class="influencer-name">
                  <strong>{{ row.display_name || row.username }}</strong>
                  <span class="sub">@{{ row.username }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="platform" :label="$t('influencer.col.platform')" width="90" />
            <el-table-column :label="$t('influencer.col.followers')" width="110" sortable prop="followers">
              <template #default="{ row }">
                {{ formatFollowers(row.followers) }}
              </template>
            </el-table-column>
            <el-table-column prop="category" :label="$t('influencer.col.category')" width="110" show-overflow-tooltip />
            <el-table-column prop="ai_score" :label="$t('influencer.col.ai_score')" width="100" sortable>
              <template #default="{ row }">
                <el-tag :type="scoreType(row.ai_score)" size="small">{{ row.ai_score?.toFixed(1) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('influencer.col.status')" width="100">
              <template #default="{ row }">
                <el-tag :type="statusTagType(row.status)" size="small">
                  {{ $t(`influencer.status.${row.status}`) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('influencer.col.action')" width="80" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="viewDetail(row)">
                  {{ $t('influencer.view_detail') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-empty v-if="!loading && influencers.length === 0" :description="$t('influencer.no_data')" />

          <!-- 分页 -->
          <div class="pagination-bar">
            <el-pagination
              v-model:current-page="currentPage"
              :page-size="pageSize"
              :total="total"
              layout="prev, pager, next, total"
              background
              small
              @current-change="fetchInfluencers"
            />
          </div>
        </el-card>
      </el-main>
    </el-container>

    <!-- 达人详情抽屉 -->
    <el-drawer
      v-model="drawerVisible"
      :title="selectedInfluencer?.display_name || selectedInfluencer?.username"
      size="420px"
    >
      <template v-if="selectedInfluencer">
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="Username">@{{ selectedInfluencer.username }}</el-descriptions-item>
          <el-descriptions-item :label="$t('influencer.col.platform')">{{ selectedInfluencer.platform }}</el-descriptions-item>
          <el-descriptions-item :label="$t('influencer.col.followers')">{{ formatFollowers(selectedInfluencer.followers) }}</el-descriptions-item>
          <el-descriptions-item :label="$t('influencer.col.category')">{{ selectedInfluencer.category }}</el-descriptions-item>
          <el-descriptions-item :label="$t('influencer.col.ai_score')">{{ selectedInfluencer.ai_score?.toFixed(1) }}</el-descriptions-item>
          <el-descriptions-item :label="$t('influencer.col.status')">
            {{ $t(`influencer.status.${selectedInfluencer.status}`) }}
          </el-descriptions-item>
          <el-descriptions-item label="Avg Views">{{ selectedInfluencer.avg_views?.toLocaleString() }}</el-descriptions-item>
          <el-descriptions-item label="GMV 30d">{{ selectedInfluencer.gmv_30d }}</el-descriptions-item>
          <el-descriptions-item label="Commission">{{ selectedInfluencer.commission_rate }}%</el-descriptions-item>
        </el-descriptions>
      </template>
    </el-drawer>
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

const categories = [
  'Beauty', 'Fashion', 'Tech', 'Lifestyle', 'Food', 'Fitness',
  'Home', 'Gaming', 'Travel', 'Education',
]

const statusOptions = computed(() => ({
  discovered:  t('influencer.status.discovered'),
  contacted:   t('influencer.status.contacted'),
  negotiating: t('influencer.status.negotiating'),
  signed:      t('influencer.status.signed'),
}))

const filter = ref({ category: '', status: '', min_followers: 0 })
const influencers = ref<any[]>([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = 20
const total = ref(0)

const drawerVisible = ref(false)
const selectedInfluencer = ref<any>(null)

function viewDetail(row: any) {
  selectedInfluencer.value = row
  drawerVisible.value = true
}

async function fetchInfluencers() {
  loading.value = true
  try {
    const params: Record<string, any> = {
      limit: pageSize,
      offset: (currentPage.value - 1) * pageSize,
      min_followers: filter.value.min_followers || 0,
    }

    if (authStore.user?.platform) {
      params.platform = authStore.user.platform
    }
    if (filter.value.category) {
      params.category = filter.value.category
    }
    if (filter.value.status) {
      params.status = filter.value.status
    }

    const res = await axios.get('/api/phase2/influencers', { params })
    influencers.value = res.data.data ?? []
    total.value = res.data.count ?? influencers.value.length
  } catch {
    ElMessage.error(t('influencer.error'))
  } finally {
    loading.value = false
  }
}

function doSearch() {
  currentPage.value = 1
  fetchInfluencers()
}

function resetFilter() {
  filter.value = { category: '', status: '', min_followers: 0 }
  currentPage.value = 1
  fetchInfluencers()
}

function formatFollowers(n: number): string {
  if (!n) return '0'
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
  return String(n)
}

function scoreType(score: number): '' | 'success' | 'warning' | 'danger' {
  if (score >= 80) return 'success'
  if (score >= 60) return 'warning'
  return 'danger'
}

function statusTagType(status: string): '' | 'success' | 'warning' | 'info' {
  const map: Record<string, any> = {
    discovered: 'info',
    contacted: 'warning',
    negotiating: '',
    signed: 'success',
  }
  return map[status] ?? 'info'
}

function logout() {
  authStore.clearToken()
  router.push('/login')
}

onMounted(() => {
  fetchInfluencers()
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
.filter-bar {
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 4px;
}
.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
.influencer-name {
  display: flex;
  flex-direction: column;
  line-height: 1.4;
}
.sub {
  font-size: 12px;
  color: #999;
}
</style>

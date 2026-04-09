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
        <span class="title">{{ $t('profile.title') }}</span>
        <el-button type="danger" plain size="small" @click="logout">{{ $t('nav.logout') }}</el-button>
      </el-header>

      <el-main class="main-content">
        <el-row :gutter="24">

          <!-- 左列：账户信息只读展示 -->
          <el-col :span="10">
            <el-card shadow="never">
              <template #header>{{ $t('profile.account_info') }}</template>
              <el-descriptions :column="1" border>
                <el-descriptions-item :label="$t('profile.username')">
                  {{ user?.username ?? '—' }}
                </el-descriptions-item>
                <el-descriptions-item :label="$t('profile.email')">
                  {{ user?.email ?? '—' }}
                </el-descriptions-item>
                <el-descriptions-item :label="$t('profile.platform')">
                  {{ user?.platform ?? '—' }}
                </el-descriptions-item>
                <el-descriptions-item :label="$t('profile.language_label')">
                  {{ user?.language === 'zh' ? $t('profile.lang_zh') : $t('profile.lang_en') }}
                </el-descriptions-item>
                <el-descriptions-item :label="$t('profile.currency_label')">
                  {{ user?.currency ?? '—' }}
                </el-descriptions-item>
                <el-descriptions-item :label="$t('profile.created_at')">
                  {{ user?.created_at ?? '—' }}
                </el-descriptions-item>
              </el-descriptions>
            </el-card>
          </el-col>

          <!-- 右列：偏好设置 + 修改密码 -->
          <el-col :span="14">

            <!-- 偏好设置 -->
            <el-card shadow="never" style="margin-bottom: 20px">
              <template #header>{{ $t('profile.preferences') }}</template>
              <el-form :model="prefsForm" label-position="top" style="max-width: 360px">
                <el-form-item :label="$t('profile.language')">
                  <el-select v-model="prefsForm.language" style="width: 100%">
                    <el-option :label="$t('profile.lang_en')" value="en" />
                    <el-option :label="$t('profile.lang_zh')" value="zh" />
                  </el-select>
                </el-form-item>
                <el-form-item :label="$t('profile.currency')">
                  <el-select v-model="prefsForm.currency" style="width: 100%">
                    <el-option :label="$t('profile.currency_cny')" value="CNY" />
                    <el-option :label="$t('profile.currency_myr')" value="MYR" />
                  </el-select>
                </el-form-item>
                <el-button type="primary" :loading="savingPrefs" @click="savePrefs">
                  {{ $t('profile.save_prefs') }}
                </el-button>
              </el-form>
            </el-card>

            <!-- 修改密码 -->
            <el-card shadow="never">
              <template #header>{{ $t('profile.change_password') }}</template>
              <el-form
                ref="pwdFormRef"
                :model="pwdForm"
                :rules="pwdRules"
                label-position="top"
                style="max-width: 360px"
              >
                <el-form-item :label="$t('profile.current_password')" prop="current_password">
                  <el-input
                    v-model="pwdForm.current_password"
                    type="password"
                    show-password
                    :placeholder="$t('profile.current_password_placeholder')"
                  />
                </el-form-item>
                <el-form-item :label="$t('profile.new_password')" prop="new_password">
                  <el-input
                    v-model="pwdForm.new_password"
                    type="password"
                    show-password
                    :placeholder="$t('profile.new_password_placeholder')"
                  />
                </el-form-item>
                <el-form-item :label="$t('profile.confirm_password')" prop="confirm_password">
                  <el-input
                    v-model="pwdForm.confirm_password"
                    type="password"
                    show-password
                    :placeholder="$t('profile.confirm_password_placeholder')"
                  />
                </el-form-item>
                <el-button type="primary" :loading="savingPwd" @click="savePassword">
                  {{ $t('profile.update_password') }}
                </el-button>
              </el-form>
            </el-card>

          </el-col>
        </el-row>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const { t } = useI18n()

const activeMenu = computed(() => route.path)
const user = computed(() => authStore.user)

// ── 偏好设置 ──────────────────────────────────────────────
const prefsForm = ref({ language: 'en', currency: 'MYR' })
const savingPrefs = ref(false)

async function savePrefs() {
  savingPrefs.value = true
  try {
    await authStore.updateProfile({
      language: prefsForm.value.language,
      currency: prefsForm.value.currency,
    })
    // 保存成功后立即切换 UI 语言
    authStore.setLocale(prefsForm.value.language)
    ElMessage.success(t('profile.save_success'))
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || t('profile.save_error'))
  } finally {
    savingPrefs.value = false
  }
}

// ── 修改密码 ──────────────────────────────────────────────
const pwdFormRef = ref<FormInstance>()
const pwdForm = ref({ current_password: '', new_password: '', confirm_password: '' })
const savingPwd = ref(false)

const pwdRules = computed<FormRules>(() => ({
  current_password: [{ required: true, message: t('validation.required_current_password'), trigger: 'blur' }],
  new_password: [
    { required: true, message: t('validation.required_new_password'), trigger: 'blur' },
    { min: 6, message: t('validation.min_password'), trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: t('validation.required_confirm_password'), trigger: 'blur' },
    {
      validator: (_rule: any, value: string, callback: any) => {
        if (value !== pwdForm.value.new_password) {
          callback(new Error(t('validation.password_mismatch')))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
}))

async function savePassword() {
  const valid = await pwdFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingPwd.value = true
  try {
    await authStore.updateProfile({
      current_password: pwdForm.value.current_password,
      new_password: pwdForm.value.new_password,
    })
    ElMessage.success(t('profile.password_success'))
    pwdForm.value = { current_password: '', new_password: '', confirm_password: '' }
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || t('profile.password_error'))
  } finally {
    savingPwd.value = false
  }
}

function logout() {
  authStore.clearToken()
  router.push('/login')
}

onMounted(async () => {
  if (!authStore.user) {
    await authStore.fetchUser()
  }
  if (authStore.user) {
    prefsForm.value.language = authStore.user.language
    prefsForm.value.currency = authStore.user.currency
  }
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
</style>

<template>
  <div class="login-wrapper">
    <el-card class="login-card" shadow="always">
      <template #header>
        <div class="card-title">{{ $t('login.title') }}</div>
      </template>
      <el-form :model="form" label-position="top" @submit.prevent="handleLogin">
        <el-form-item :label="$t('login.email')">
          <el-input v-model="form.email" :placeholder="$t('login.email_placeholder')" type="email" />
        </el-form-item>
        <el-form-item :label="$t('login.password')">
          <el-input v-model="form.password" :placeholder="$t('login.password_placeholder')" type="password" show-password />
        </el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading" style="width: 100%">
          {{ $t('login.submit') }}
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const { t } = useI18n()

const form = ref({ email: '', password: '' })
const loading = ref(false)

async function handleLogin() {
  loading.value = true
  try {
    const res = await axios.post('/api/auth/login', form.value)
    authStore.setToken(res.data.access_token)
    await authStore.fetchUser()
    const redirect = (route.query.redirect as string) || '/'
    router.push(redirect)
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || t('login.error'))
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background: #f0f2f5;
}
.login-card {
  width: 400px;
}
.card-title {
  text-align: center;
  font-size: 20px;
  font-weight: bold;
}
</style>

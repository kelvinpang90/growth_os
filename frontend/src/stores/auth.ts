import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'
import { i18n } from '@/i18n'

interface UserProfile {
  id: number
  username: string
  email: string
  platform: string
  language: string
  currency: string
  created_at: string
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const user = ref<UserProfile | null>(null)

  const isLoggedIn = computed(() => !!token.value)

  function setToken(newToken: string) {
    token.value = newToken
    localStorage.setItem('access_token', newToken)
    axios.defaults.headers.common['Authorization'] = `Bearer ${newToken}`
  }

  function clearToken() {
    token.value = null
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_language')
    delete axios.defaults.headers.common['Authorization']
  }

  function setLocale(lang: string) {
    const locale = (lang === 'en' ? 'en' : 'zh') as 'zh' | 'en'
    i18n.global.locale.value = locale
    localStorage.setItem('user_language', locale)
  }

  async function fetchUser() {
    if (!token.value) return
    axios.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
    const res = await axios.get('/api/auth/me')
    user.value = res.data
    setLocale(res.data.language)
  }

  async function updateProfile(payload: {
    current_password?: string
    new_password?: string
    language?: string
    currency?: string
  }) {
    const res = await axios.patch('/api/auth/me', payload)
    user.value = res.data
    return res.data
  }

  return { token, user, isLoggedIn, setToken, clearToken, fetchUser, updateProfile, setLocale }
})

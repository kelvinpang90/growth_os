import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const user = ref<{ id: number; username: string; email: string } | null>(null)

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
    delete axios.defaults.headers.common['Authorization']
  }

  async function fetchUser() {
    if (!token.value) return
    axios.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
    const res = await axios.get('/api/auth/me')
    user.value = res.data
  }

  return { token, user, isLoggedIn, setToken, clearToken, fetchUser }
})

import { defineStore } from 'pinia'
import { getCurrentUser, login, type CurrentUser } from '@/api/auth'
import { ACCESS_TOKEN_KEY, CURRENT_USER_KEY, clearStoredAuth } from '@/utils/authSession'

function readStoredUser(): CurrentUser | null {
  const raw = localStorage.getItem(CURRENT_USER_KEY)
  if (!raw) return null
  try {
    const value = JSON.parse(raw) as unknown
    if (!value || typeof value !== 'object') throw new Error('Invalid stored user')
    return value as CurrentUser
  } catch {
    localStorage.removeItem(CURRENT_USER_KEY)
    return null
  }
}

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem(ACCESS_TOKEN_KEY) || '',
    user: readStoredUser(),
  }),
  getters: {
    isLoggedIn: (state) => Boolean(state.token),
    displayName: (state) => state.user?.display_name || state.user?.username || '未登录',
  },
  actions: {
    async login(username: string, password: string) {
      const res = await login({ username, password })
      this.token = res.access_token
      this.user = res.user
      localStorage.setItem(ACCESS_TOKEN_KEY, res.access_token)
      localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(res.user))
      return res.user
    },
    async loadCurrentUser() {
      if (!this.token) return null
      this.user = await getCurrentUser()
      localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(this.user))
      return this.user
    },
    logout() {
      this.token = ''
      this.user = null
      clearStoredAuth()
    },
  },
})

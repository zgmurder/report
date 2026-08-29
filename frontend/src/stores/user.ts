import { defineStore } from 'pinia'
import { getCurrentUser, login, type CurrentUser } from '@/api/auth'

const TOKEN_KEY = 'report_access_token'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) || '',
    user: JSON.parse(localStorage.getItem('report_current_user') || 'null') as CurrentUser | null,
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
      localStorage.setItem(TOKEN_KEY, res.access_token)
      localStorage.setItem('report_current_user', JSON.stringify(res.user))
      return res.user
    },
    async loadCurrentUser() {
      if (!this.token) return null
      this.user = await getCurrentUser()
      localStorage.setItem('report_current_user', JSON.stringify(this.user))
      return this.user
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem('report_current_user')
    },
  },
})

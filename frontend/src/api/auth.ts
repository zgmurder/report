import { apiGet, apiPost } from './request'

export interface CurrentUser {
  id: number
  username: string
  display_name: string
  roles: string[]
  unit_code?: string | null
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: CurrentUser
}

export function login(data: { username: string; password: string }) {
  return apiPost<LoginResponse>('/auth/login', data)
}

export function getCurrentUser() {
  return apiGet<CurrentUser>('/auth/me')
}

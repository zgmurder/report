import axios from 'axios'
import { ACCESS_TOKEN_KEY, redirectToLogin } from '@/utils/authSession'

export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

request.interceptors.request.use((config) => {
  const token = localStorage.getItem(ACCESS_TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use((response) => {
  const payload = response.data as ApiResponse<unknown>
  if (payload && typeof payload.code === 'number' && payload.code !== 0) {
    return Promise.reject(new Error(payload.message || '请求失败'))
  }
  return response
}, (error) => {
  if (error?.response?.status === 401) redirectToLogin()
  const detail = error?.response?.data?.detail
  const message = Array.isArray(detail) ? detail[0]?.msg : detail
  return Promise.reject(new Error(message || error?.message || '请求失败'))
})

export async function apiGet<T>(url: string): Promise<T> {
  const res = await request.get<ApiResponse<T>>(url)
  return res.data.data
}

export async function apiPost<T>(
  url: string,
  data?: unknown,
  config?: { signal?: AbortSignal; timeout?: number },
): Promise<T> {
  const res = await request.post<ApiResponse<T>>(url, data, config)
  return res.data.data
}

export async function apiPut<T>(url: string, data?: unknown): Promise<T> {
  const res = await request.put<ApiResponse<T>>(url, data)
  return res.data.data
}

export async function apiDelete<T>(url: string): Promise<T> {
  const res = await request.delete<ApiResponse<T>>(url)
  return res.data.data
}

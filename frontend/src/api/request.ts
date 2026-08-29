import axios from 'axios'

export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

request.interceptors.response.use((response) => {
  const payload = response.data as ApiResponse<unknown>
  if (payload && typeof payload.code === 'number' && payload.code !== 0) {
    return Promise.reject(new Error(payload.message || '请求失败'))
  }
  return response
})

export async function apiGet<T>(url: string): Promise<T> {
  const res = await request.get<ApiResponse<T>>(url)
  return res.data.data
}

export async function apiPost<T>(url: string, data?: unknown): Promise<T> {
  const res = await request.post<ApiResponse<T>>(url, data)
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

/** 兼容旧页面期望的 RuoYi 风格响应外壳：{ data } */

export interface DataEnvelope<T> {
  data: T
}

export function wrapData<T>(data: T): DataEnvelope<T> {
  return { data }
}

export function buildQuery(params?: Record<string, unknown>): string {
  if (!params) return ''
  const query = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    query.append(key, String(value))
  })
  const text = query.toString()
  return text ? `?${text}` : ''
}

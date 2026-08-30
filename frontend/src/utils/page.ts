/** 兼容旧页面对列表/分页响应的读取方式 */

export interface PageEnvelope<T = unknown> {
  data?: T | { rows?: T; total?: number }
  rows?: T
  total?: number
  modelContent?: {
    rows?: T
    total?: number
  }
}

export function getPageRows<T>(res: PageEnvelope<T[]> | null | undefined): T[] {
  if (!res) return []
  if (Array.isArray(res.modelContent?.rows)) return res.modelContent.rows
  const data = res.data
  if (data && typeof data === 'object' && !Array.isArray(data) && Array.isArray((data as { rows?: T[] }).rows)) {
    return (data as { rows: T[] }).rows
  }
  if (Array.isArray(data)) return data
  if (Array.isArray(res.rows)) return res.rows
  return []
}

export function getResponseData<T>(res: { data?: T } | null | undefined): T | undefined {
  return res?.data
}

export function getPageTotal(res: PageEnvelope<unknown> | null | undefined): number {
  if (!res) return 0
  const modelTotal = res.modelContent?.total
  if (typeof modelTotal === 'number') return modelTotal
  const data = res.data
  if (data && typeof data === 'object' && !Array.isArray(data)) {
    const nestedTotal = (data as { total?: number }).total
    if (typeof nestedTotal === 'number') return nestedTotal
  }
  if (typeof res.total === 'number') return res.total
  return getPageRows(res as PageEnvelope<unknown[]>).length
}

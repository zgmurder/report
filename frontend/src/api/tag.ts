import { apiDelete, apiGet, apiPost, apiPut } from './request'
import { buildQuery, wrapData, type DataEnvelope } from '@/utils/apiEnvelope'
import { ACCESS_TOKEN_KEY, handleUnauthorizedResponse } from '@/utils/authSession'

export interface SmartTag {
  id: string
  name: string
  category: string
  source: string
  description?: string
}

export interface SelectedSmartTag extends SmartTag {
  mode: 'include' | 'exclude'
}

export interface JudgmentPackage {
  id: string
  name: string
  createdAt: string
  remark: string
  tags: SelectedSmartTag[]
  preset?: boolean
}

export interface TagAlarmRow {
  id: string
  cjdbh?: string | null
  bjsj?: string | null
  fkdwmc?: string | null
  fkrxm?: string | null
  ywsj_dt?: string | null
  cjqk?: string | null
  result?: string | null
  resultOriginal?: string | null
  result_original?: string | null
  manualVerified?: boolean
  verifiedBy?: string | null
  verifiedAt?: string | null
  canRestore?: boolean
}

export interface TagCatalog {
  categories: string[]
  tags: SmartTag[]
}

export interface TagSearchPayload {
  tags?: SelectedSmartTag[]
  sortKey?: 'policeStation' | 'incidentCount' | 'bjsj'
  sortAsc?: boolean
  selectedIds?: string[]
  pageNum?: number
  pageSize?: number
  cjdbh?: string
  fkdwmc?: string
  fkrxm?: string
  keyword?: string
  beginTime?: string
  endTime?: string
  includeTags?: string[]
  excludeTags?: string[]
  manualVerified?: boolean
}

export interface AlarmVerifyPersonPayload {
  name?: string
  idNo?: string
  phone?: string
  nationality?: string
  roles?: string[]
  tags?: string[]
  identities?: string[]
}

export interface AlarmVerifyPayload {
  id: string
  alarmTags: string[]
  dispose: string[]
  times: string[]
  places: string[]
  people?: AlarmVerifyPersonPayload[]
  relationsText?: string
}

export interface TagSearchResult {
  columns?: string[]
  rows: TagAlarmRow[]
  total: number
  pageNum?: number
  pageSize?: number
  sql?: string | null
  incidentTotal?: number
  stationTotal?: number
  peopleTotal?: number
}

export async function listTagCatalog(sheet?: string): Promise<DataEnvelope<TagCatalog>> {
  const query = buildQuery(sheet && sheet !== '全部' ? { sheet } : undefined)
  const data = await apiGet<TagCatalog>(`/tags/catalog${query}`)
  return wrapData(data)
}

export async function listTagPackages(keyword?: string): Promise<DataEnvelope<JudgmentPackage[]>> {
  const query = buildQuery({ keyword })
  const data = await apiGet<JudgmentPackage[]>(`/tags/packages${query}`)
  return wrapData(data)
}

export async function saveTagPackage(data: {
  name: string
  remark?: string
  tags: SelectedSmartTag[]
}): Promise<DataEnvelope<{ id: string }>> {
  const result = await apiPost<{ id: string }>('/tags/packages', data)
  return wrapData(result)
}

export async function updateTagPackage(
  id: string,
  data: { name: string; remark?: string; tags: SelectedSmartTag[] },
): Promise<DataEnvelope<{ id: string }>> {
  const result = await apiPut<{ id: string }>(`/tags/packages/${id}`, data)
  return wrapData(result)
}

export async function deleteTagPackage(id: string): Promise<DataEnvelope<unknown>> {
  const result = await apiDelete(`/tags/packages/${id}`)
  return wrapData(result)
}

export async function searchTags(data: TagSearchPayload): Promise<DataEnvelope<TagSearchResult>> {
  const includeFromTags = (data.tags || []).filter((item) => item.mode === 'include').map((item) => item.name)
  const excludeFromTags = (data.tags || []).filter((item) => item.mode === 'exclude').map((item) => item.name)
  const includeTags = [...includeFromTags, ...(data.includeTags || [])].filter(Boolean)
  const excludeTags = [...excludeFromTags, ...(data.excludeTags || [])].filter(Boolean)
  const query = buildQuery({
    tags: includeTags.join(','),
    excludeTags: excludeTags.join(','),
    sortKey: data.sortKey || 'bjsj',
    sortAsc: data.sortAsc ?? false,
    pageNum: data.pageNum || 1,
    pageSize: data.pageSize || 10,
    cjdbh: data.cjdbh || undefined,
    fkdwmc: data.fkdwmc || undefined,
    fkrxm: data.fkrxm || undefined,
    keyword: data.keyword || undefined,
    beginTime: data.beginTime || undefined,
    endTime: data.endTime || undefined,
    manualVerified: typeof data.manualVerified === 'boolean' ? data.manualVerified : undefined,
  })
  const result = await apiGet<TagSearchResult>(`/tags/search${query}`)
  return wrapData(result)
}

export async function verifyAlarmTags(data: AlarmVerifyPayload): Promise<DataEnvelope<TagAlarmRow>> {
  const result = await apiPut<TagAlarmRow>('/tags/alarms/verify', data)
  return wrapData(result)
}

export async function restoreAlarmTags(id: string): Promise<DataEnvelope<TagAlarmRow>> {
  const result = await apiPut<TagAlarmRow>('/tags/alarms/restore', { id })
  return wrapData(result)
}

export async function exportTags(data: TagSearchPayload & { exportType?: 'alarms' | 'people' }) {
  const exportType = data.exportType || 'alarms'
  const token = localStorage.getItem(ACCESS_TOKEN_KEY)
  const response = await fetch('/api/v1/tags/export', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      tags: data.tags,
      sortKey: data.sortKey,
      sortAsc: data.sortAsc,
      selectedIds: data.selectedIds,
      pageNum: 1,
      pageSize: 10000,
      exportType,
      beginTime: data.beginTime || undefined,
      endTime: data.endTime || undefined,
      cjdbh: data.cjdbh || undefined,
      fkdwmc: data.fkdwmc || undefined,
      fkrxm: data.fkrxm || undefined,
      keyword: data.keyword || undefined,
    }),
  })
  if (handleUnauthorizedResponse(response)) throw new Error('登录状态已失效，请重新登录')
  if (!response.ok) {
    let message = '导出失败'
    try {
      const payload = await response.json()
      message = payload?.message || payload?.detail || message
    } catch {
      /* ignore */
    }
    throw new Error(message)
  }
  return response.blob()
}

export function parseTagResult(resultRaw?: string | null): Record<string, unknown> {
  if (!resultRaw) return {}
  try {
    const data = JSON.parse(resultRaw)
    return data && typeof data === 'object' ? (data as Record<string, unknown>) : {}
  } catch {
    return {}
  }
}

export function extractTagsFromAlarmRow(row: TagAlarmRow): string[] {
  const data = parseTagResult(row.result)
  const tags = new Set<string>()
  const timePlace = data['时间地点']
  if (timePlace && typeof timePlace === 'object') {
    Object.values(timePlace as Record<string, unknown>).forEach((value) => {
      if (Array.isArray(value)) value.forEach((item) => item && tags.add(String(item)))
      else if (value) tags.add(String(value))
    })
  }
  Object.entries(data).forEach(([key, value]) => {
    if (['时间地点', '人物关系', '人物分析', '处置结果'].includes(key)) return
    if (Array.isArray(value)) value.forEach((item) => item && tags.add(String(item)))
  })
  const dispose = data['处置结果']
  if (Array.isArray(dispose)) dispose.forEach((item) => item && tags.add(String(item)))
  const people = data['人物分析']
  if (Array.isArray(people)) {
    people.forEach((person) => {
      if (!person || typeof person !== 'object') return
      ;(['人物标签', '人物身份', '事件角色'] as const).forEach((key) => {
        const values = (person as Record<string, unknown>)[key]
        if (Array.isArray(values)) values.forEach((item) => item && tags.add(String(item)))
      })
    })
  }
  return [...tags]
}

export function extractPeopleFromAlarmRow(row: TagAlarmRow): Array<Record<string, unknown>> {
  const data = parseTagResult(row.result)
  const people = data['人物分析']
  return Array.isArray(people) ? (people as Array<Record<string, unknown>>) : []
}

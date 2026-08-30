import { apiGet, apiPut } from './request'
import { buildQuery, wrapData, type DataEnvelope } from '@/utils/apiEnvelope'

export interface TagV2DictItem {
  id: string
  tagCode: string
  domain: string
  level1?: string
  level2?: string
  level3?: string
  level4?: string
  tagPath: string
  tagRule?: string
  method?: string
  name: string
  category: string
}

export interface TagV2ResultItem {
  id?: number
  tagCode: string
  tagPath: string
  domain: string
  source: string
  confidence?: number | null
  evidence?: string | null
  batch?: string | null
  tagRule?: string | null
  method?: string | null
  createTime?: string | null
  name: string
}

export interface TagV2PersonTagItem {
  id?: number
  tagCode?: string | null
  tagPath: string
  source?: string | null
  enrichStatus?: string | null
  evidence?: string | null
  batch?: string | null
  createTime?: string | null
  name?: string
}

export interface TagV2PersonItem {
  idNo?: string | null
  personName?: string | null
  phone?: string | null
  personRole: string
  personRoleLabel?: string
  enrichStatus?: string | null
  tags: TagV2PersonTagItem[]
  zjTags?: TagV2PersonTagItem[]
}

export interface TagV2AlarmRow {
  id: string
  fkdbh: string
  cjdbh?: string | null
  jjdbh?: string | null
  bjsj?: string | null
  fkdwmc?: string | null
  fkdwdm?: string | null
  zrmj?: string | null
  fkrxm?: string | null
  cjqk?: string | null
  jqqh?: string | null
  jqxz?: string | null
  czyj?: string | null
  tagCount?: number
  personCount?: number
  manualVerified?: boolean
  lastTagTime?: string | null
  tags?: TagV2ResultItem[]
  persons?: TagV2PersonItem[]
}

export interface TagV2Catalog {
  domains: string[]
  tags: TagV2DictItem[]
  dataRange?: {
    beginTime?: string | null
    endTime?: string | null
    alarmCount?: number
  }
}

export interface TagV2SearchPayload {
  includeTags?: string[]
  excludeTags?: string[]
  domain?: string
  fkdbh?: string
  cjdbh?: string
  fkdwmc?: string
  fkdwdm?: string
  fkrxm?: string
  keyword?: string
  beginTime?: string
  endTime?: string
  hasManual?: boolean
  ajlbCodes?: string[]
  ajlxCodes?: string[]
  ajxlCodes?: string[]
  pageNum?: number
  pageSize?: number
}

export interface TagV2SearchResult {
  rows: TagV2AlarmRow[]
  total: number
  pageNum?: number
  pageSize?: number
}

export type TagV2StatsLevel = '1' | '2' | '3' | '4' | 'combo'

export interface TagV2StatsItem {
  label: string
  pathPrefix: string
  alarmCount: number
  hitCount: number
}

export interface TagV2StatsResult {
  level: TagV2StatsLevel | string
  totalAlarms: number
  items: TagV2StatsItem[]
}

function buildTagV2QueryParams(data: TagV2SearchPayload) {
  return {
    tags: (data.includeTags || []).join(',') || undefined,
    excludeTags: (data.excludeTags || []).join(',') || undefined,
    domain: data.domain || undefined,
    fkdbh: data.fkdbh || undefined,
    cjdbh: data.cjdbh || undefined,
    fkdwmc: data.fkdwmc || undefined,
    fkdwdm: data.fkdwdm || undefined,
    fkrxm: data.fkrxm || undefined,
    keyword: data.keyword || undefined,
    beginTime: data.beginTime || undefined,
    endTime: data.endTime || undefined,
    hasManual: typeof data.hasManual === 'boolean' ? data.hasManual : undefined,
    ajlb: (data.ajlbCodes || []).join(',') || undefined,
    ajlx: (data.ajlxCodes || []).join(',') || undefined,
    ajxl: (data.ajxlCodes || []).join(',') || undefined,
  }
}

export async function listTagV2Catalog(domain?: string): Promise<DataEnvelope<TagV2Catalog>> {
  const query = buildQuery(domain && domain !== '全部' ? { domain } : undefined)
  const data = await apiGet<TagV2Catalog>(`/tags-v2/catalog${query}`)
  return wrapData(data)
}

export async function statsTagV2Alarms(
  data: TagV2SearchPayload & { level?: TagV2StatsLevel; limit?: number },
): Promise<DataEnvelope<TagV2StatsResult>> {
  const query = buildQuery({
    ...buildTagV2QueryParams(data),
    level: data.level || '1',
    limit: data.limit || 500,
  })
  const result = await apiGet<TagV2StatsResult>(`/tags-v2/stats${query}`)
  return wrapData(result)
}

export async function searchTagV2Alarms(
  data: TagV2SearchPayload,
): Promise<DataEnvelope<TagV2SearchResult>> {
  const query = buildQuery({
    ...buildTagV2QueryParams(data),
    pageNum: data.pageNum || 1,
    pageSize: data.pageSize || 20,
  })
  const result = await apiGet<TagV2SearchResult>(`/tags-v2/search${query}`)
  return wrapData(result)
}

export async function getTagV2AlarmDetail(fkdbh: string): Promise<DataEnvelope<TagV2AlarmRow>> {
  const data = await apiGet<TagV2AlarmRow>(`/tags-v2/alarms/${encodeURIComponent(fkdbh)}`)
  return wrapData(data)
}

export async function verifyTagV2Alarm(data: {
  fkdbh: string
  tagPaths: string[]
}): Promise<DataEnvelope<TagV2AlarmRow>> {
  const result = await apiPut<TagV2AlarmRow>('/tags-v2/alarms/verify', data)
  return wrapData(result)
}

export function groupTagsByDomain(tags: TagV2ResultItem[] | undefined | null) {
  const grouped = new Map<string, TagV2ResultItem[]>()
  ;(tags || []).forEach((tag) => {
    const domain = String(tag.domain || '未分类').trim() || '未分类'
    const list = grouped.get(domain) || []
    list.push(tag)
    grouped.set(domain, list)
  })
  return [...grouped.entries()].map(([domain, items]) => ({ domain, items }))
}

const PERSON_ROLE_LABELS: Record<string, string> = {
  bjr: '报警人',
  sxr: '涉事人',
  shr: '受害人',
  xyr: '嫌疑人',
  qtr: '其他人员',
}

export function personRoleLabel(role?: string | null) {
  const key = String(role || '').trim().toLowerCase()
  return PERSON_ROLE_LABELS[key] || String(role || '').trim() || '涉警人员'
}

export function enrichStatusLabel(status?: string | null) {
  const map: Record<string, string> = {
    '0': '标签待补全',
    '1': '已补全',
    '2': '无命中',
    '9': '补全失败',
  }
  return map[String(status || '0')] || '标签待补全'
}

export function personDisplayName(person: TagV2PersonItem) {
  return String(person.personName || person.idNo || '未知').trim() || '未知'
}

export function personTagLeaf(tag: TagV2PersonTagItem) {
  const path = String(tag.tagPath || '').trim()
  return tag.name || path.split('/').filter(Boolean).pop() || path || '-'
}

export function isZjPersonTag(tag: TagV2PersonTagItem) {
  const source = String(tag.source || '').trim().toLowerCase()
  if (source === 'zj-api' || source === 'third_party') return true
  return String(tag.tagPath || '').startsWith('治安标签/')
}

export function personExtractTags(person: TagV2PersonItem) {
  return (person.tags || []).filter((tag) => !isZjPersonTag(tag))
}

export function personZjTags(person: TagV2PersonItem) {
  if (person.zjTags?.length) return person.zjTags
  return (person.tags || []).filter((tag) => isZjPersonTag(tag))
}

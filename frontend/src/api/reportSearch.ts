import { apiGet, apiPost, apiPut } from './request'

export interface SearchDepartment {
  code: string
  name: string
}

export interface SearchDataSource {
  key: string
  name: string
  enabled: boolean
}

export interface SearchOptions {
  current_department: SearchDepartment
  data_sources: SearchDataSource[]
  default_start_time: string
  default_end_time: string
}

export interface SearchClassificationItem {
  code: string
  name: string
}

export interface SearchClassificationResponse {
  source: string
  level: 'category' | 'type' | 'detail'
  items: SearchClassificationItem[]
}

export interface StatisticsDictionarySource {
  source: 'jjd_jjd' | 'fkd_fkd'
  name: string
  categories: SearchClassificationItem[]
  types: SearchClassificationItem[]
  details: SearchClassificationItem[]
  disabled: {
    category: string[]
    type: string[]
    detail: string[]
  }
}

export interface StatisticsDictionaryConfig {
  sources: StatisticsDictionarySource[]
}

export interface SearchMetric {
  key: string
  label: string
  description: string
  default: boolean
}

export interface SearchMetrics {
  source: string
  dimensions: SearchMetric[]
  measures: SearchMetric[]
}

export interface SearchQuery {
  source: 'jjd_jjd' | 'fkd_fkd'
  start_time: string
  end_time: string
  category_codes: string[]
  type_codes: string[]
  detail_codes: string[]
  dimensions: string[]
  measures: string[]
  limit: number
}

export interface SearchResultColumn {
  key: string
  label: string
  type: 'text' | 'number' | 'datetime'
}

export interface SearchResult {
  source: SearchDataSource
  department: SearchDepartment
  columns: SearchResultColumn[]
  rows: Record<string, unknown>[]
  row_count: number
  elapsed_ms: number
  truncated: boolean
}

export function getReportSearchOptions() {
  return apiGet<SearchOptions>('/report-search/options')
}

export function getStatisticsDictionaryConfig() {
  return apiGet<StatisticsDictionaryConfig>('/report-search/dictionary-config')
}

export function updateStatisticsDictionaryConfig(data: {
  source: 'jjd_jjd' | 'fkd_fkd'
  disabled_categories: string[]
  disabled_types: string[]
  disabled_details: string[]
}) {
  return apiPut<StatisticsDictionarySource>('/report-search/dictionary-config', data)
}

export function getReportSearchClassifications(
  source: string,
  level: 'category' | 'type' | 'detail',
  parentCode?: string,
) {
  const params = new URLSearchParams({ source, level })
  if (parentCode) params.set('parent_code', parentCode)
  return apiGet<SearchClassificationResponse>(`/report-search/classifications?${params.toString()}`)
}

export function getReportSearchMetrics(source = 'jjd_jjd') {
  return apiGet<SearchMetrics>(`/report-search/metrics?source=${encodeURIComponent(source)}`)
}

export function executeReportSearch(data: SearchQuery) {
  return apiPost<SearchResult>('/report-search/query', data)
}

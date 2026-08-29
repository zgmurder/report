import { apiGet } from './request'

export interface ReportTemplateItem {
  id: number
  name: string
  category: string
  description: string
  content_json?: Record<string, unknown>
  status: string
  created_at: string
  updated_at: string
}

export interface StatComponentItem {
  id: number
  name: string
  component_type: string
  data_source: string
  usage: string
  config_json: Record<string, unknown>
  status: string
  created_at: string
  updated_at: string
}

export interface DataSourceItem {
  id: number
  name: string
  source_type: string
  address: string
  description: string
  config_json: Record<string, unknown>
  status: string
  created_at: string
  updated_at: string
}

export function listTemplates() {
  return apiGet<ReportTemplateItem[]>('/catalog/templates')
}

export function listComponents() {
  return apiGet<StatComponentItem[]>('/catalog/components')
}

export function listDataSources() {
  return apiGet<DataSourceItem[]>('/catalog/data-sources')
}

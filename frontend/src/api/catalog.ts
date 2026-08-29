import { apiDelete, apiGet, apiPost, apiPut } from './request'

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

export type TemplatePayload = Partial<Pick<ReportTemplateItem, 'name' | 'category' | 'description' | 'content_json' | 'status'>>
export type ComponentPayload = Partial<Pick<StatComponentItem, 'name' | 'component_type' | 'data_source' | 'usage' | 'config_json' | 'status'>>
export type DataSourcePayload = Partial<Pick<DataSourceItem, 'name' | 'source_type' | 'address' | 'description' | 'config_json' | 'status'>>

export function listTemplates() {
  return apiGet<ReportTemplateItem[]>('/catalog/templates')
}

export function createTemplate(data: TemplatePayload) {
  return apiPost<ReportTemplateItem>('/catalog/templates', data)
}

export function updateTemplate(id: number, data: TemplatePayload) {
  return apiPut<ReportTemplateItem>(`/catalog/templates/${id}`, data)
}

export function deleteTemplate(id: number) {
  return apiDelete<{ deleted: boolean }>(`/catalog/templates/${id}`)
}

export function listComponents() {
  return apiGet<StatComponentItem[]>('/catalog/components')
}

export function createComponent(data: ComponentPayload) {
  return apiPost<StatComponentItem>('/catalog/components', data)
}

export function updateComponent(id: number, data: ComponentPayload) {
  return apiPut<StatComponentItem>(`/catalog/components/${id}`, data)
}

export function deleteComponent(id: number) {
  return apiDelete<{ deleted: boolean }>(`/catalog/components/${id}`)
}

export function listDataSources() {
  return apiGet<DataSourceItem[]>('/catalog/data-sources')
}

export function createDataSource(data: DataSourcePayload) {
  return apiPost<DataSourceItem>('/catalog/data-sources', data)
}

export function updateDataSource(id: number, data: DataSourcePayload) {
  return apiPut<DataSourceItem>(`/catalog/data-sources/${id}`, data)
}

export function deleteDataSource(id: number) {
  return apiDelete<{ deleted: boolean }>(`/catalog/data-sources/${id}`)
}

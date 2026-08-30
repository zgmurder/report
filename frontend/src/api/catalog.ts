import { apiDelete, apiGet, apiPost, apiPut } from './request'

export interface ReportTemplateItem {
  id: number
  name: string
  description: string
  content_json?: Record<string, unknown>
  original_filename?: string | null
  file_size?: number | null
  mime_type?: string | null
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

export type TemplatePayload = Partial<Pick<ReportTemplateItem, 'name' | 'description' | 'content_json' | 'status'>>
export type ComponentPayload = Partial<Pick<StatComponentItem, 'name' | 'component_type' | 'data_source' | 'usage' | 'config_json' | 'status'>>
export type DataSourcePayload = Partial<Pick<DataSourceItem, 'name' | 'source_type' | 'address' | 'description' | 'config_json' | 'status'>>

export function listTemplates() {
  return apiGet<ReportTemplateItem[]>('/catalog/templates')
}

export function createTemplate(data: TemplatePayload) {
  return apiPost<ReportTemplateItem>('/catalog/templates', data)
}

export function uploadTemplate(file: File, data: { name?: string; description?: string; status?: string }) {
  const form = new FormData()
  form.append('file', file)
  if (data.name) form.append('name', data.name)
  form.append('description', data.description || '')
  form.append('status', data.status || 'enabled')
  return apiPost<ReportTemplateItem>('/catalog/templates/upload', form)
}

export interface ReportTemplateContent {
  id: number
  name: string
  original_filename: string
  html: string
}

export function getTemplateContent(id: number) {
  return apiGet<ReportTemplateContent>(`/catalog/templates/${id}/content`)
}

export async function downloadTemplate(id: number, filename: string) {
  const token = localStorage.getItem('report_access_token')
  const response = await fetch(`/api/v1/catalog/templates/${id}/download`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) throw new Error(response.status === 404 ? '该模板没有可下载的 Word 文件' : '模板下载失败')
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename || '报告模板.docx'
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
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

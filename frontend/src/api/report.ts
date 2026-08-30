import { apiDelete, apiGet, apiPost, apiPut } from './request'

export interface ReportSection {
  id: string
  title: string
  type: string
  content?: string | null
  blocks: Array<Record<string, unknown>>
  source: string[]
  ai_generated: boolean
}

export interface EditorPageMargin {
  left: number
  right: number
  top: number
  bottom: number
  layout?: string
}

export interface EditorPageSize {
  label?: string | Record<string, string> | null
  width?: number | null
  height?: number | null
}

export interface EditorPageConfig {
  orientation: 'portrait' | 'landscape'
  margin: EditorPageMargin
  layout: 'page' | 'web'
  background: string
  size?: EditorPageSize | null
}

export interface ReportEditorConfig {
  page: EditorPageConfig
}

export interface ReportContent {
  title: string
  type: string
  params: Record<string, unknown>
  sections: ReportSection[]
}

export interface ReportItem {
  id: number
  title: string
  report_type: string
  status: string
  folder_id?: number | null
  created_at: string
  updated_at: string
  source_query?: Record<string, unknown>
  editor_config?: ReportEditorConfig
  content_json?: ReportContent | null
  draft_json?: ReportContent | null
  html_snapshot?: string | null
}

export function listReports() {
  return apiGet<ReportItem[]>('/reports')
}

export interface ReportFolderItem {
  id: number
  name: string
  parent_id?: number | null
  sort_order: number
  report_count: number
  created_at: string
  updated_at: string
}

export function createReport(data: { title: string; report_type: string; source_query: Record<string, unknown>; folder_id?: number | null }) {
  return apiPost<ReportItem>('/reports', data)
}

export function listReportFolders() {
  return apiGet<ReportFolderItem[]>('/reports/folders')
}

export function createReportFolder(data: { name: string; parent_id?: number | null }) {
  return apiPost<ReportFolderItem>('/reports/folders', data)
}

export function updateReportFolder(id: number, data: { name?: string; parent_id?: number | null; sort_order?: number }) {
  return apiPut<ReportFolderItem>(`/reports/folders/${id}`, data)
}

export function deleteReportFolder(id: number) {
  return apiDelete<{ deleted: boolean }>(`/reports/folders/${id}`)
}

export function getReport(id: number) {
  return apiGet<ReportItem>(`/reports/${id}`)
}

export function updateReport(id: number, data: { title?: string; folder_id?: number | null; status?: string }) {
  return apiPut<ReportItem>(`/reports/${id}`, data)
}

export function deleteReport(id: number) {
  return apiDelete<{ deleted: boolean }>(`/reports/${id}`)
}

export function confirmReportDraft(id: number) {
  return apiPost<ReportItem>(`/reports/${id}/confirm`)
}

export function exportReportHtmlUrl(id: number) {
  return `/api/v1/reports/${id}/export-html`
}

async function readableDownloadError(response: Response, fallback: string) {
  try {
    const data = await response.json() as { detail?: string }
    return data.detail || fallback
  } catch {
    return fallback
  }
}

export async function downloadReportDocx(id: number, title: string) {
  const token = localStorage.getItem('report_access_token')
  const response = await fetch(`/api/v1/reports/${id}/export-docx`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) throw new Error(await readableDownloadError(response, 'Word 导出失败'))
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${title || '报告'}.docx`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export function generateReportDraft(id: number, data: { report_type: string; source_query: Record<string, unknown> }) {
  return apiPost<{ draft_json: ReportContent; explanation: string; warnings: string[] }>(`/reports/${id}/generate-draft`, data)
}

export function saveReportContent(id: number, content_json: ReportContent, html_snapshot: string | undefined, editor_config: ReportEditorConfig) {
  return apiPut<ReportItem>(`/reports/${id}/content`, { content_json, html_snapshot, editor_config })
}

export function saveReportDraft(id: number, content_json: ReportContent, html_snapshot: string | undefined, editor_config: ReportEditorConfig) {
  return apiPut<ReportItem>(`/reports/${id}/draft`, { content_json, html_snapshot, editor_config })
}

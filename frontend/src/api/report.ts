import { apiGet, apiPost, apiPut } from './request'

export interface ReportSection {
  id: string
  title: string
  type: string
  content?: string | null
  blocks: Array<Record<string, unknown>>
  source: string[]
  ai_generated: boolean
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
  created_at: string
  updated_at: string
  source_query?: Record<string, unknown>
  content_json?: ReportContent | null
  draft_json?: ReportContent | null
}

export function listReports() {
  return apiGet<ReportItem[]>('/reports')
}

export function createReport(data: { title: string; report_type: string; source_query: Record<string, unknown> }) {
  return apiPost<ReportItem>('/reports', data)
}

export function getReport(id: number) {
  return apiGet<ReportItem>(`/reports/${id}`)
}

export function generateReportDraft(id: number, data: { report_type: string; source_query: Record<string, unknown> }) {
  return apiPost<{ draft_json: ReportContent; explanation: string; warnings: string[] }>(`/reports/${id}/generate-draft`, data)
}

export function saveReportContent(id: number, content_json: ReportContent) {
  return apiPut<ReportItem>(`/reports/${id}/content`, { content_json })
}

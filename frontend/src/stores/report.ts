import { defineStore } from 'pinia'
import {
  createReport,
  generateReportDraft,
  createReportFolder,
  deleteReport,
  deleteReportFolder,
  getReport,
  listReportFolders,
  listReports,
  saveReportContent,
  updateReport,
  updateReportFolder,
  type ReportContent,
  type ReportFolderItem,
  type ReportItem,
} from '@/api/report'

export const useReportStore = defineStore('report', {
  state: () => ({
    reports: [] as ReportItem[],
    folders: [] as ReportFolderItem[],
    currentReport: null as ReportItem | null,
    editingContent: null as ReportContent | null,
    htmlSnapshot: '',
  }),
  actions: {
    async loadReports() {
      this.reports = await listReports()
      return this.reports
    },
    async loadFolders() {
      this.folders = await listReportFolders()
      return this.folders
    },
    async createFolder(name: string, parentId?: number | null) {
      const folder = await createReportFolder({ name, parent_id: parentId })
      await this.loadFolders()
      return folder
    },
    async createBlankReport(title = '未命名警情报告', folderId?: number | null) {
      const report = await createReport({ title, report_type: 'incident', source_query: {}, folder_id: folderId })
      await this.loadReports()
      this.currentReport = report
      return report
    },
    async renameFolder(id: number, name: string) {
      const folder = await updateReportFolder(id, { name })
      await this.loadFolders()
      return folder
    },
    async removeFolder(id: number) {
      await deleteReportFolder(id)
      await Promise.all([this.loadFolders(), this.loadReports()])
    },
    async renameReport(id: number, title: string) {
      const report = await updateReport(id, { title })
      await this.loadReports()
      if (this.currentReport?.id === id) this.currentReport = report
      return report
    },
    async moveReport(id: number, folderId: number | null) {
      const report = await updateReport(id, { folder_id: folderId })
      await this.loadReports()
      if (this.currentReport?.id === id) this.currentReport = report
      return report
    },
    async removeReport(id: number) {
      await deleteReport(id)
      await this.loadReports()
      if (this.currentReport?.id === id) {
        this.currentReport = null
        this.editingContent = null
        this.htmlSnapshot = ''
      }
    },
    async loadReport(id: number) {
      this.currentReport = await getReport(id)
      const content = this.currentReport.content_json || this.currentReport.draft_json
      this.editingContent = content ? structuredClone(content) : null
      this.htmlSnapshot = this.currentReport.html_snapshot || ''
    },
    async generateDraft(id: number, reportType = 'monthly', sourceQuery: Record<string, unknown> = {}) {
      const result = await generateReportDraft(id, { report_type: reportType, source_query: sourceQuery })
      this.editingContent = result.draft_json
      await this.loadReport(id)
      return result
    },
    async save(id: number, content?: ReportContent, htmlSnapshot?: string) {
      const target = content || this.editingContent
      if (!target) return
      this.currentReport = await saveReportContent(id, target, htmlSnapshot ?? this.htmlSnapshot)
      this.editingContent = this.currentReport.content_json || target
      this.htmlSnapshot = this.currentReport.html_snapshot || htmlSnapshot || ''
      await this.loadReports()
    },
  },
})

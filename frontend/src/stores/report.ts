import { defineStore } from 'pinia'
import { toRaw } from 'vue'
import {
  confirmReportDraft,
  createReport,
  generateReportDraft,
  createReportFolder,
  deleteReport,
  deleteReportFolder,
  getReport,
  listReportFolders,
  listReports,
  saveReportContent,
  saveReportDraft,
  updateReport,
  updateReportFolder,
  type ReportContent,
  type ReportEditorConfig,
  type ReportFolderItem,
  type ReportItem,
} from '@/api/report'

let reportLoadSequence = 0
const saveQueues = new Map<number, Promise<unknown>>()

export const useReportStore = defineStore('report', {
  state: () => ({
    reports: [] as ReportItem[],
    folders: [] as ReportFolderItem[],
    currentReport: null as ReportItem | null,
    editingContent: null as ReportContent | null,
    htmlSnapshot: '',
    editorConfig: null as ReportEditorConfig | null,
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
      await Promise.all([this.loadReports(), this.loadFolders()])
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
      await Promise.all([this.loadReports(), this.loadFolders()])
      if (this.currentReport?.id === id) this.currentReport = report
      return report
    },
    async removeReport(id: number) {
      await deleteReport(id)
      await Promise.all([this.loadReports(), this.loadFolders()])
      if (this.currentReport?.id === id) {
        this.currentReport = null
        this.editingContent = null
        this.htmlSnapshot = ''
        this.editorConfig = null
      }
    },
    async loadReport(id: number) {
      const sequence = ++reportLoadSequence
      const report = await getReport(id)
      if (sequence !== reportLoadSequence) return null
      this.applyLoadedReport(report)
      return report
    },
    applyLoadedReport(report: ReportItem) {
      this.currentReport = report
      let content: ReportContent | null | undefined
      switch (report.status) {
        case 'draft':
          content = report.draft_json || report.content_json
          break
        case 'confirmed':
        case 'archived':
          content = report.content_json
          break
        default: {
          const exhaustive: never = report.status
          throw new Error(`不支持的报告状态：${exhaustive}`)
        }
      }
      this.editingContent = content ? structuredClone(toRaw(content)) : null
      this.htmlSnapshot = report.html_snapshot || ''
      this.editorConfig = report.editor_config ? structuredClone(toRaw(report.editor_config)) : null
    },
    async generateDraft(id: number, reportType = 'monthly', sourceQuery: Record<string, unknown> = {}) {
      const result = await generateReportDraft(id, { report_type: reportType, source_query: sourceQuery })
      this.editingContent = result.draft_json
      await this.loadReport(id)
      return result
    },
    async confirmDraft(id: number) {
      await saveQueues.get(id)?.catch(() => undefined)
      const report = await confirmReportDraft(id)
      await this.loadReport(id)
      await this.loadReports()
      return report
    },
    async save(id: number, content: ReportContent | undefined, htmlSnapshot: string | undefined, editorConfig: ReportEditorConfig) {
      const target = content || this.editingContent
      if (!target) return
      const report = this.currentReport
      if (!report || report.id !== id) throw new Error('当前报告已切换，请重新保存')
      if (report.status === 'archived') throw new Error('归档报告为只读，不能保存')
      const status = report.status
      const previous = saveQueues.get(id) || Promise.resolve()
      const operation = previous.catch(() => undefined).then(() => {
        const saveRequest = status === 'confirmed' ? saveReportContent : saveReportDraft
        return saveRequest(id, target, htmlSnapshot ?? this.htmlSnapshot, editorConfig)
      })
      saveQueues.set(id, operation)
      let saved: ReportItem
      try {
        saved = await operation
      } finally {
        if (saveQueues.get(id) === operation) saveQueues.delete(id)
      }
      if (this.currentReport?.id !== id) return
      reportLoadSequence += 1
      this.applyLoadedReport(saved)
      const summary = this.reports.find((item) => item.id === id)
      if (summary) {
        summary.title = saved.title
        summary.status = saved.status
        summary.folder_id = saved.folder_id
        summary.updated_at = saved.updated_at
        this.reports.sort((left, right) => right.updated_at.localeCompare(left.updated_at) || right.id - left.id)
      }
    },
  },
})

import { defineStore } from 'pinia'
import { getReport, saveReportContent, type ReportContent, type ReportItem } from '@/api/report'

export const useReportStore = defineStore('report', {
  state: () => ({
    currentReport: null as ReportItem | null,
    editingContent: null as ReportContent | null,
  }),
  actions: {
    async loadReport(id: number) {
      this.currentReport = await getReport(id)
      const content = this.currentReport.content_json || this.currentReport.draft_json
      this.editingContent = content ? structuredClone(content) : null
    },
    async save(id: number, content?: ReportContent) {
      const target = content || this.editingContent
      if (!target) return
      this.currentReport = await saveReportContent(id, target)
      this.editingContent = this.currentReport.content_json || target
    },
  },
})

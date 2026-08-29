import { defineStore } from 'pinia'
import {
  createComponent,
  createDataSource,
  createTemplate,
  deleteComponent,
  deleteDataSource,
  deleteTemplate,
  listComponents,
  listDataSources,
  listTemplates,
  updateComponent,
  updateDataSource,
  updateTemplate,
  type ComponentPayload,
  type DataSourceItem,
  type DataSourcePayload,
  type ReportTemplateItem,
  type StatComponentItem,
  type TemplatePayload,
} from '@/api/catalog'

export const useCatalogStore = defineStore('catalog', {
  state: () => ({
    templates: [] as ReportTemplateItem[],
    components: [] as StatComponentItem[],
    dataSources: [] as DataSourceItem[],
  }),
  actions: {
    async loadTemplates() {
      this.templates = await listTemplates()
      return this.templates
    },
    async saveTemplate(data: TemplatePayload, id?: number) {
      const result = id ? await updateTemplate(id, data) : await createTemplate(data)
      await this.loadTemplates()
      return result
    },
    async removeTemplate(id: number) {
      await deleteTemplate(id)
      await this.loadTemplates()
    },
    async loadComponents() {
      this.components = await listComponents()
      return this.components
    },
    async saveComponent(data: ComponentPayload, id?: number) {
      const result = id ? await updateComponent(id, data) : await createComponent(data)
      await this.loadComponents()
      return result
    },
    async removeComponent(id: number) {
      await deleteComponent(id)
      await this.loadComponents()
    },
    async loadDataSources() {
      this.dataSources = await listDataSources()
      return this.dataSources
    },
    async saveDataSource(data: DataSourcePayload, id?: number) {
      const result = id ? await updateDataSource(id, data) : await createDataSource(data)
      await this.loadDataSources()
      return result
    },
    async removeDataSource(id: number) {
      await deleteDataSource(id)
      await this.loadDataSources()
    },
  },
})

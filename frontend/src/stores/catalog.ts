import { defineStore } from 'pinia'
import {
  listComponents,
  listDataSources,
  listTemplates,
  type DataSourceItem,
  type ReportTemplateItem,
  type StatComponentItem,
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
    async loadComponents() {
      this.components = await listComponents()
      return this.components
    },
    async loadDataSources() {
      this.dataSources = await listDataSources()
      return this.dataSources
    },
  },
})

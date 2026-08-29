import { defineStore } from 'pinia'
import { listDepartments, type DepartmentItem } from '@/api/department'

export const useDepartmentStore = defineStore('department', {
  state: () => ({
    departments: [] as DepartmentItem[],
  }),
  getters: {
    options: (state) =>
      state.departments.map((item) => ({
        label: item.name,
        value: item.code,
      })),
  },
  actions: {
    async loadDepartments() {
      this.departments = await listDepartments()
      return this.departments
    },
  },
})

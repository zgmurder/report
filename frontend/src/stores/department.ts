import { defineStore } from 'pinia'
import type { TreeSelectOption } from 'naive-ui'
import { listDepartments, listDepartmentTree, type DepartmentItem } from '@/api/department'

export const useDepartmentStore = defineStore('department', {
  state: () => ({
    departments: [] as DepartmentItem[],
    departmentTree: [] as DepartmentItem[],
  }),
  getters: {
    options: (state) => toOptions(state.departments),
    treeOptions: (state) => toOptions(state.departmentTree),
  },
  actions: {
    async loadDepartments() {
      this.departments = await listDepartments()
      return this.departments
    },
    async loadDepartmentTree() {
      this.departmentTree = await listDepartmentTree()
      return this.departmentTree
    },
  },
})

function toOptions(items: DepartmentItem[]): TreeSelectOption[] {
  return items.map((item) => {
    const children = item.children?.length ? toOptions(item.children) : undefined
    return {
      label: item.name,
      key: item.code,
      ...(children ? { children } : {}),
    }
  })
}

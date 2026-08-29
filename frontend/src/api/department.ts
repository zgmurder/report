import { apiDelete, apiGet, apiPost, apiPut } from './request'

export interface DepartmentItem {
  id: number
  name: string
  code: string
  parent_id?: number | null
  sort_order: number
  status: string
  created_at: string
  updated_at: string
  children?: DepartmentItem[]
}

export function listDepartments() {
  return apiGet<DepartmentItem[]>('/departments')
}

export function listDepartmentTree() {
  return apiGet<DepartmentItem[]>('/departments/tree')
}

export function createDepartment(data: { name: string; code: string; parent_id?: number | null; sort_order?: number; status?: string }) {
  return apiPost<DepartmentItem>('/departments', data)
}

export function updateDepartment(id: number, data: { name?: string; code?: string; parent_id?: number | null; sort_order?: number; status?: string }) {
  return apiPut<DepartmentItem>(`/departments/${id}`, data)
}

export function deleteDepartment(id: number) {
  return apiDelete<{ deleted: boolean }>(`/departments/${id}`)
}

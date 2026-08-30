import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { listDepartmentTree, type DepartmentItem } from '@/api/department'
import { useUserStore } from '@/stores/user'
import { flattenDepartmentTree } from '@/utils/deptTree'

/** 市局部门码：有效数字去尾 0 后长度 ≤ 6（如 330782000000） */
export function isCityBureauDept(deptCode?: string | null, deptName?: string | null) {
  const name = String(deptName || '').trim()
  if (name.includes('市局')) return true
  const digits = String(deptCode || '').replace(/\D/g, '')
  if (!digits) return false
  const stripped = digits.replace(/0+$/, '') || digits
  return stripped.length <= 6
}

function findDeptByCode(items: DepartmentItem[], code: string): DepartmentItem | null {
  const target = String(code || '').trim()
  if (!target) return null
  for (const item of items) {
    if (String(item.code || '').trim() === target) return item
    if (item.children?.length) {
      const found = findDeptByCode(item.children, target)
      if (found) return found
    }
  }
  return null
}

/**
 * 兼容旧工作台页面对 useAuthStore 的用法：
 * deptId / deptCode / deptName / isCityBureau / token / loadUserInfo
 */
export const useAuthStore = defineStore('workbenchAuth', () => {
  const userStore = useUserStore()
  const departmentTree = ref<DepartmentItem[]>([])

  const token = computed(() => userStore.token)
  const deptCode = computed(() => String(userStore.user?.unit_code || '').trim())
  const matchedDept = computed(() => findDeptByCode(departmentTree.value, deptCode.value))
  const deptId = computed(() => (matchedDept.value ? String(matchedDept.value.id) : ''))
  const deptName = computed(() => String(matchedDept.value?.name || '').trim())
  const isCityBureau = computed(() => isCityBureauDept(deptCode.value, deptName.value))

  async function ensureDepartmentTree() {
    if (departmentTree.value.length) return departmentTree.value
    departmentTree.value = await listDepartmentTree()
    return departmentTree.value
  }

  async function loadUserInfo() {
    if (!userStore.user && userStore.token) {
      await userStore.loadCurrentUser()
    }
    await ensureDepartmentTree()
  }

  async function listScopedDeptOptions() {
    const tree = await ensureDepartmentTree()
    return flattenDepartmentTree(tree)
  }

  return {
    deptCode,
    deptId,
    deptName,
    isCityBureau,
    listScopedDeptOptions,
    loadUserInfo,
    token,
  }
})

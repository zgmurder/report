import { Bookmark, FileText, ShieldAlert, Tags } from 'lucide-vue-next'
import type { Component } from 'vue'

export interface WorkbenchNavItem {
  key: string
  title: string
  path: string
  icon: Component
  desc: string
}

export const workbenchNavItems: WorkbenchNavItem[] = [
  { key: 'reports', title: '智能报告', path: '/home/reports', icon: FileText, desc: '报告编制工作台' },
  { key: 'tags', title: '研判包', path: '/home/tags', icon: Bookmark, desc: '人员与线索研判' },
  { key: 'warnings', title: '预警', path: '/home/warnings', icon: ShieldAlert, desc: '风险监测预警' },
  { key: 'alarm-tagging', title: '警情打标', path: '/home/alarm-tagging', icon: Tags, desc: '警情多标签标注' },
]

import { apiGet } from './request'
import { getReportSearchClassifications } from './reportSearch'
import { wrapData, type DataEnvelope } from '@/utils/apiEnvelope'

export interface FeedbackCategoryNode {
  code: string
  name: string
  parentCode?: string
  level: 'category' | 'type' | 'subtype'
  children?: FeedbackCategoryNode[]
}

/**
 * 反馈类别树：优先走后端 /components/feedback-category-tree（若已实现）；
 * 否则用 report-search 分类接口拼一层扁平树（类型/细类暂无父子关系）。
 * TODO: 后端提供专用反馈类别树或完整父子码映射后，去掉 report-search 退化逻辑。
 */
export async function getFeedbackCategoryTree(): Promise<DataEnvelope<FeedbackCategoryNode[]>> {
  try {
    const data = await apiGet<FeedbackCategoryNode[]>('/components/feedback-category-tree')
    return wrapData(Array.isArray(data) ? data : [])
  } catch {
    // fallback
  }

  try {
    const [categories, types, details] = await Promise.all([
      getReportSearchClassifications('fkd_fkd', 'category'),
      getReportSearchClassifications('fkd_fkd', 'type'),
      getReportSearchClassifications('fkd_fkd', 'detail'),
    ])
    // 无父子码映射时，退化为并列选项：类别带空 children，类型/细类由页面 flatten 收集
    const typeNodes: FeedbackCategoryNode[] = (types.items || []).map((item) => ({
      code: item.code,
      name: item.name,
      level: 'type',
      children: (details.items || []).map((detail) => ({
        code: detail.code,
        name: detail.name,
        parentCode: item.code,
        level: 'subtype' as const,
      })),
    }))
    const tree: FeedbackCategoryNode[] = (categories.items || []).map((item, index) => ({
      code: item.code,
      name: item.name,
      level: 'category',
      // 仅第一个类别挂上全部类型，保证 flattenFeedbackOptions 能收集到类型/细类选项
      children: index === 0 ? typeNodes : [],
    }))
    return wrapData(tree)
  } catch {
    return wrapData([])
  }
}

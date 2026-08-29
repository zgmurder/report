import type { GlobalThemeOverrides } from 'naive-ui'

/** 对齐现有警情工作台主色 #1890ff */
export const naiveThemeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#1890ff',
    primaryColorHover: '#40a9ff',
    primaryColorPressed: '#096dd9',
    primaryColorSuppl: '#1890ff',
    borderRadius: '4px',
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Helvetica Neue", Arial, sans-serif',
  },
  Button: {
    borderRadiusMedium: '4px',
    heightMedium: '32px',
  },
  Input: {
    borderRadius: '4px',
    heightMedium: '32px',
  },
  Select: {
    peers: {
      InternalSelection: {
        heightMedium: '32px',
        borderRadius: '4px',
      },
    },
  },
  Tabs: {
    tabTextColorActiveLine: '#1890ff',
    tabTextColorHoverLine: '#40a9ff',
    barColor: '#1890ff',
  },
}

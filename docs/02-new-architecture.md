# 新系统主体架构

## 定位

本项目是高度定制化的“警情智能报告”系统，不是通用后台管理框架。

## 后端分层

```text
Router / API
  -> Application Service
  -> Domain Service / Infrastructure
  -> Repository / Database / External Client
```

- Router：HTTP 参数、鉴权依赖、统一响应。
- Service：业务编排，例如生成报告、保存草稿、人工确认。
- Repository：数据库访问，SQL 必须集中、参数绑定。
- Domain：报告结构校验、AI 客户端、警情领域规则。

## 前端分层

```text
View / Page
  -> Store / Composable
  -> API Client
  -> Component
```

- View 负责页面布局和业务组合。
- Store 保存当前用户、当前报告、编辑副本。
- API Client 统一请求与错误处理。
- Component 后续承载报告块、图表、警情引用等展示能力。

## 数据原则

- 报告结构化 JSON 是权威数据。
- HTML、Docx、PDF 是导出产物。
- AI 只生成 draft_json，人工确认后才写入 content_json。
- 警情大列表必须分页，避免一次性加载。

## 第一阶段闭环

1. 健康检查。
2. 登录/当前用户占位。
3. 警情查询与统计接口骨架。
4. 报告新建、列表、详情、AI 草稿、人工确认保存。
5. 前端报告中心与三栏编辑工作台。

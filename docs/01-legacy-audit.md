# 旧项目资产盘点

旧项目路径：`E:/project/2026-6/yw-police-intelligence-ruoyi-fastapi`

## 可迁移资产

- 后端警情业务：`ruoyi-fastapi-backend/module_intelligence`
  - 报告、组件、模板、数据源相关 controller/service。
  - SQL 组件执行、组件渲染、导出、AI 组件生成等能力。
- 后端 AI：`ruoyi-fastapi-backend/module_ai`
  - 模型管理、聊天/流式调用、AI 工具封装。
- SQL：`ruoyi-fastapi-backend/sql/intelligence`
  - 智能报告表结构、组件 SQL、标签体系等。
- 前端警情页面：`ruoyi-fastapi-frontend/src/views/intelligence`
  - 报告、模板、组件、数据源、文件夹等页面流程。
- 独立报告编辑探索：`ruoyi-fastapi-tiptap-report`、`editor`
  - 报告工作台、编辑器、侧边栏、组件输出等交互参考。

## 应丢弃内容

- 若依系统管理、动态菜单、代码生成器、监控、字典、岗位、公告等通用后台。
- 若依式前端权限指令、动态路由、菜单 SQL、复杂管理端布局。
- 与警情智能报告无关的通用 CRUD 生成能力。

## 新项目迁移策略

旧项目只作为业务样本，不直接复制框架结构。迁移时按领域重建：警情、统计、报告、模板、组件、AI、导出、权限数据范围。

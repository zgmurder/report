# 警情智能报告

轻量、可维护、高度定制化的警情智能报告系统。旧若依项目仅作为业务参考，本项目按 `AGENT.md` / `AGENTS.md` 规则重新建设。

## 目录

```text
backend   FastAPI 后端
frontend  Vue3 前端
docs      设计与迁移文档
scripts   本地启动脚本
```

## 开发启动

后端：

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

前端：

```bash
cd frontend
npm install
npm run dev
```

## 验证

```bash
python -m compileall -q backend/app backend/tests
cd frontend && npm run build
```

## 核心原则

- 去若依化，不做通用后台。
- 后端 Router -> Service -> Repository。
- 前端 View -> Store -> API Client -> Component。
- 报告结构化 JSON 是权威数据。
- AI 只生成草稿，人工确认后保存。
- SQL 参数绑定，敏感配置进入环境变量。

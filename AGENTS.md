# 项目协作与运行说明

本项目是“警情智能报告”系统，目标是轻量、可维护、可验证、高度定制化。旧若依项目仅作为业务参考，不直接复制框架结构。

## 项目定位

- 系统定位：警情智能报告工作台。
- 后端：FastAPI 服务，按 `Router -> Service -> Repository` 分层。
- 前端：Vue3 + Naive UI，按 `View -> Store/Composable -> API Client -> Component` 分层。
- 报告数据：结构化 JSON 是权威数据，HTML / Docx / PDF 均为派生产物。
- AI 能力：默认只生成草稿，必须经过校验和人工确认后保存。

## 开发约束

- SQL 必须使用参数绑定，禁止拼接用户输入。
- 敏感配置只允许放入 `.env` 或环境变量，禁止提交真实密钥。
- 前端 UI 组件库使用 Naive UI，主题主色为 `#1890ff`。
- 图标可使用 `lucide-vue-next`。
- 保持代码简单清晰，避免引入通用后台式复杂结构。

## 启动项目

Windows 环境优先执行一键启动脚本，会同时启动后端和前端，并记录可用于整棵进程树关闭的 PID：

```bat
scripts\start-project.bat
```

启动后访问：

- 前端：`http://localhost:5173/`
- 后端：`http://127.0.0.1:8001`
- 后端健康检查：`http://127.0.0.1:8001/health`

在类 Unix / Git Bash 环境也可手动执行：

```bash
rm -f backend-uvicorn.pid frontend-vite.pid
mkdir -p logs
(
  cd backend || exit 1
  WATCHFILES_FORCE_POLLING=true PYTHONUNBUFFERED=1 nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload --reload-dir app --reload-include '*.py' --reload-delay 0.5 > ../logs/backend-uvicorn.log 2> ../logs/backend-uvicorn-error.log &
  echo $! > ../backend-uvicorn.pid
)
(
  cd frontend || exit 1
  nohup npm run dev -- --host 0.0.0.0 > ../logs/frontend-vite.log 2> ../logs/frontend-vite-error.log &
  echo $! > ../frontend-vite.pid
)
```

也可以在 Windows 终端分别执行：

```bat
scripts\start-backend.bat
scripts\start-frontend.bat
```

## 关闭项目

Windows 环境优先执行一键关闭脚本，会同时关闭主进程和子进程，并兜底释放 `8001` / `5173` 端口：

```bat
scripts\stop-project.bat
```

在类 Unix / Git Bash 环境也可手动执行：

```bash
if [ -f backend-uvicorn.pid ]; then kill $(cat backend-uvicorn.pid) 2>/dev/null || true; rm -f backend-uvicorn.pid; fi
if [ -f frontend-vite.pid ]; then kill $(cat frontend-vite.pid) 2>/dev/null || true; rm -f frontend-vite.pid; fi
```

如端口仍被占用，可查看占用进程：

```bash
netstat -ano | grep -E ':(8001|5173)\s'
```

## 日志文件

日志文件统一保存到 `logs/` 目录：

- 后端标准输出：`logs/backend-uvicorn.log`
- 后端错误输出：`logs/backend-uvicorn-error.log`
- 前端标准输出：`logs/frontend-vite.log`
- 前端错误输出：`logs/frontend-vite-error.log`

## 验证命令

在提交或交付前执行：

```bash
python -m compileall -q backend/app backend/tests
cd frontend && npm run build
cd .. && git diff --check
```

也可分开执行：

- 后端：`python -m compileall -q backend/app backend/tests`
- 前端：`cd frontend && npm run build`
- 通用：`git diff --check`

## 工程速览与开发经验

### 目录与入口

- 后端目录：`backend/`，FastAPI + SQLAlchemy + PyMySQL。
- 后端入口：`backend/app/main.py`，负责创建 FastAPI app、配置 CORS、启动时调用 `init_db()`、暴露 `/health`、挂载 API 总路由。
- 后端 API 总路由：`backend/app/api/v1/router.py`，统一前缀默认是 `/api/v1`。
- 前端目录：`frontend/`，Vue 3 + Vite + Pinia + Naive UI。
- 前端入口：`frontend/src/main.ts`，注册 Pinia 和 Router。
- 前端顶层：`frontend/src/App.vue`，放置 Naive UI 全局 Provider 和顶层 `router-view`。
- 前端路由：`frontend/src/router/index.ts`，`/login` 公开，`/home/*` 需要登录。
- 主布局：`frontend/src/layouts/WorkbenchLayout.vue`。
- 顶部导航配置：`frontend/src/data/navigation.ts`。

### 后端分层约定

- 严格按 `Router -> Service -> Repository` 分层：
  - `backend/app/api/v1/*.py`：路由层，只做 HTTP 参数绑定、依赖注入、调用 service、返回 `ok(...)`。
  - `backend/app/services/*.py`：业务层，做业务校验、权限/状态冲突处理、组合仓储和领域服务。
  - `backend/app/repositories/*.py`：仓储层，做 SQLAlchemy 查询、事务提交、ORM 到 schema 转换。
  - `backend/app/models/*.py`：SQLAlchemy ORM 模型。
  - `backend/app/schemas/*.py`：Pydantic 请求/响应模型。
- 统一响应封装在 `backend/app/core/response.py`，前端期望格式：`{ code, message, data }`。
- 认证与权限在 `backend/app/core/security.py`：
  - 当前用户依赖：`get_current_user()`。
  - 管理员依赖：`require_admin()`。
  - 当前用户结构：`CurrentUser`。
- 除 `/auth` 外，多数 API 都在 `router.py` 里加了 `Depends(get_current_user)`；`/users`、`/pi-agent` 等需要 `require_admin`。

### 数据库与配置

- 配置集中在 `backend/app/core/config.py`，使用 Pydantic Settings，可由 `.env` 或环境变量覆盖。
- 关键配置：`DATABASE_URL`、`JWT_SECRET_KEY`、`JWT_EXPIRE_MINUTES`、`ADMIN_PASSWORD`、`CORS_ORIGINS`、Pi Agent/LLM 相关开关。
- 数据库连接和 session 在 `backend/app/core/database.py`：`engine`、`SessionLocal`、`Base`、`get_db()`、`init_db()`。
- 默认数据库是 MySQL：`mysql+pymysql://...?...charset=utf8mb4`。
- `init_db()` 会 `Base.metadata.create_all(bind=engine)`，并包含部分 MySQL 历史字段/字符集补偿逻辑；复杂迁移不要散落到业务代码里。
- SQL 必须使用参数绑定；仓储层优先用 SQLAlchemy 表达式，避免字符串拼接用户输入。

### 报告模块是最佳参考实现

新增业务时优先参考报告模块完整链路：

- 路由：`backend/app/api/v1/reports.py`
- 服务：`backend/app/services/report_service.py`
- 仓储：`backend/app/repositories/report_repository.py`
- ORM：`backend/app/models/report.py`
- Schema：`backend/app/schemas/report.py`
- 前端 API：`frontend/src/api/report.ts`
- 前端 Store：`frontend/src/stores/report.ts`
- 页面：`frontend/src/views/HomeView.vue`、`frontend/src/views/EditorView.vue`

报告数据以结构化 JSON 为权威数据，HTML / Docx / PDF 都是派生产物。AI 只生成草稿，必须校验并人工确认后保存。

### 主要后端 API 模块

统一前缀：`/api/v1`。

- 登录认证：`/auth/login`、`/auth/me`。
- 报告：`/reports/*`，含报告 CRUD、文件夹、草稿、确认、导出 HTML/Docx。
- 警情查询：`/police-events/search`、`/police-events/overview`。
- 报告统计检索：`/report-search/*`，含选项、字典配置、分类、指标、查询、批量查询。
- 原子指标：`/atomic-metric/query`。
- 研判包/标签：`/tags/*`、`/tags-v2/*`。
- 预警：`/warnings/*`。
- 目录配置：`/catalog/templates`、`/catalog/components`、`/catalog/data-sources`。
- 组织用户：`/departments/*`、`/users/*`。
- Pi Agent：`/pi-agent/*`，管理员权限，默认配置可能关闭。

### 前端开发约定

- API client 统一从 `frontend/src/api/request.ts` 导出的 `apiGet/apiPost/apiPut/apiDelete` 调用。
- `request.ts` 设置 `baseURL: '/api/v1'`，自动附加 Bearer token，统一处理响应 envelope 和 401 跳转。
- Vite 代理在 `frontend/vite.config.ts`：`/api` 转发到 `http://127.0.0.1:8001`，端口固定 `5173`。
- 用户登录态在 `frontend/src/stores/user.ts`，token 存储 key 来自 `frontend/src/constants/auth.ts`。
- 核心业务状态：
  - 报告：`frontend/src/stores/report.ts`
  - 目录：`frontend/src/stores/catalog.ts`
  - 部门：`frontend/src/stores/department.ts`
- 新增前端页面通常按这个顺序：
  1. 新增或扩展 `frontend/src/api/xxx.ts`；
  2. 必要时新增 `frontend/src/stores/xxx.ts`；
  3. 新增 `frontend/src/views/XxxView.vue`；
  4. 在 `frontend/src/router/index.ts` 注册路由；
  5. 如需出现在顶部导航，修改 `frontend/src/data/navigation.ts`。
- UI 使用 Naive UI，主题主色保持 `#1890ff`；图标优先使用 `lucide-vue-next`。

### 新功能开发建议

- 后端新增模块建议步骤：
  1. 定义/修改 ORM：`backend/app/models/`；
  2. 定义 Pydantic schema：`backend/app/schemas/`；
  3. 写 Repository：`backend/app/repositories/`；
  4. 写 Service：`backend/app/services/`；
  5. 写 Router：`backend/app/api/v1/`；
  6. 在 `backend/app/api/v1/router.py` 挂载；
  7. 补充必要测试或至少运行 compileall。
- 前后端字段要以 schema/API client 类型为准，避免页面里写散乱的临时字段。
- 遇到权限问题先检查 `router.py` 的依赖、`CurrentUser`、以及仓储层是否按当前用户范围过滤。
- 遇到前端请求问题先检查：浏览器登录态 token、`request.ts` envelope 解包、Vite `/api` 代理、后端 `/health`。
- 遇到启动/端口问题优先使用：`scripts\stop-project.bat` 后再 `scripts\start-project.bat`。
- 日志统一看 `logs/`，不要在项目根目录新增散乱 `.log` 文件。

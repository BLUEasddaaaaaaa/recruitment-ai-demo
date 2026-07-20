# 招聘 AI Demo（React 前端 + Python 后端 + SQLite）

一个可本地运行的招聘 AI 应用：**AI Studio 设计的 React 企业级招聘工作台** 连接 **Codex 实现的 Python 招聘流程逻辑**，数据持久化在 **SQLite**。

- 前端：`frontend/`（Vite + React + Tailwind），企业级招聘 SaaS 界面
- 后端：`src/`（FastAPI + SQLite + AI 解析），提供真实招聘业务能力
- 不再依赖前端 mock 数据，所有数据均来自 Python 后端与 SQLite

## 目录结构

```text
recruitment-ai-demo/
├── frontend/              # AI Studio React 前端（Vite + React + Tailwind）
├── src/                   # Python 后端核心逻辑
├── src/api/               # FastAPI REST 接口层（本 Demo 新增）
├── data/                  # SQLite 数据库（自动创建，已 gitignore）
├── samples/               # 匿名简历样本
├── scripts/               # 启动脚本
├── 启动完整招聘AI-Demo.command  # 一键启动前后端（macOS）
└── README.md
```

## 一键启动（推荐，macOS）

直接双击项目根目录下的 **`启动完整招聘AI-Demo.command`**：

1. 自动创建 Python 虚拟环境并安装依赖
2. 启动 Python FastAPI 后端：`http://localhost:8000`
3. 启动 React 前端：`http://localhost:3000`
4. 自动打开浏览器

关闭启动窗口会同时停止前后端。

## 手动启动

### 后端（Python FastAPI）

需要 Python 3.12+。

```bash
cd recruitment-ai-demo
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
export AI_MODE=fake            # 离线演示模式，无需任何 API Key
uvicorn src.api.main:app --reload --port 8000
```

后端健康检查：`http://localhost:8000/api/health`

### 前端（React）

需要 Node.js 18+（建议 pnpm）。

```bash
cd recruitment-ai-demo/frontend
pnpm install          # 或 npm install
pnpm run dev          # 或 npm run dev
```

访问：`http://localhost:3000`

前端通过环境变量 `VITE_API_BASE_URL` 连接后端（默认 `http://localhost:8000`），
见 `frontend/.env.example`。

## REST 接口一览

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/resume/parse` | 简历文本 → 结构化候选人字段（含置信度） |
| POST | `/api/candidates` | HR 确认后写入候选人 + 申请 |
| GET | `/api/candidates` | 候选人流程列表（含面试记录） |
| GET | `/api/candidates/{id}` | 候选人详情 |
| PUT | `/api/applications/{id}/status` | 更新筛选状态（待定/通过/拒绝等） |
| POST | `/api/applications/{id}/interviews` | 追加面试轮次（不覆盖历史） |
| GET | `/api/ai/dashboard` | AI 运营助手：待办 / 洞察 / 企业微信汇报 |

## 演示路径

1. 简历智能录入：粘贴/上传简历 → 点击「开始 AI 智能提取」→ 核对并「确认入库」。
2. 候选人全流程：按岗位/部门/状态/HR 筛选、关键词搜索；点击行查看详情、更新状态、追加面试记录。
3. AI 招聘运营助手：基于真实数据生成今日待办、运营洞察、一键企业微信汇报。

## 运行模式

- 默认 `AI_MODE=fake`：使用本地确定性解析，全程离线，无需密钥。
- 真实 AI 模式（可选）：
  ```bash
  export AI_MODE=real
  export OPENAI_API_KEY='your-key'
  export OPENAI_MODEL='your-model'
  ```

## 当前限制

- 附件仅保存安全元数据与哈希引用，不提供原文件下载。
- 仅支持受控、匿名化输入，不应上传真实个人敏感信息。

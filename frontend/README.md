# 智聘 AI 工作台 React 前端原型

这是 AI Studio 生成并整合进项目的新版前端原型，技术栈为 Vite + React + Tailwind + Express。

## 定位

该前端用于展示更完整的企业级招聘工作台视觉方案：

- 左侧导航
- 顶部状态栏
- 简历智能录入
- 招聘台账筛选和候选人详情
- AI 招聘运营助手

它当前使用自己的 Express mock API 和本地 JSON 数据，不直接连接 Streamlit Demo 的 SQLite 数据库。

## 运行

```bash
pnpm install
pnpm run dev
```

默认访问：

```text
http://localhost:3000/
```

## 构建

```bash
pnpm run build
pnpm run start
```

如需调用 Gemini，请复制 `.env.example` 为 `.env.local` 并配置 `GEMINI_API_KEY`。不配置时会使用离线 mock 模式。


# React 前端说明

这是招聘 AI Demo 的 React 前端，技术栈为 Vite + React + Tailwind。

当前版本已经连接 Python FastAPI 后端，默认 API 地址为：

```text
http://localhost:8000
```

配置文件：

```text
frontend/.env.example
```

默认配置：

```env
VITE_API_BASE_URL=http://localhost:8000
```

## 运行

先启动后端：

```bash
cd ..
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
AI_MODE=fake uvicorn src.api.main:app --reload --port 8000
```

再启动前端：

```bash
cd frontend
npm install
npm run dev
```

访问：

```text
http://localhost:3000
```

## 说明

- 主演示链路为 React 前端 + Python FastAPI 后端 + SQLite。
- 页面中的候选人列表、简历解析、候选人入库、状态更新、面试记录和 AI 运营助手均通过后端接口完成。
- `VITE_DEMO_MODE=1` 仅用于纯前端静态预览，不是主演示模式。


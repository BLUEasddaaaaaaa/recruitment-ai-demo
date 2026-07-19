import path from "path";
import express from "express";
import { createServer as createViteServer } from "vite";

const app = express();
const PORT = 3000;

// Development server for the React front-end.
// The front-end talks to the Python FastAPI backend (default http://localhost:8000)
// configured via VITE_API_BASE_URL. This server only serves the SPA in dev.
async function startServer() {
  const vite = await createViteServer({
    server: { middlewareMode: true },
    appType: "spa",
  });
  app.use(vite.middlewares);

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`React 前端开发服务器已启动: http://0.0.0.0:${PORT}`);
  });
}

startServer();

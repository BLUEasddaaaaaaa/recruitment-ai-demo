# 智聘 AI 工作台 - 企业微信与腾讯文档第三方集成方案文档

本篇文档详细说明了如何将本 **AI 招聘工作台** 与 **企业微信 (WeCom)** 和 **腾讯文档 (Tencent Docs)** 进行深度 API 级对接，实现招聘消息自动推送（群机器人）、台账数据双向同步等高级功能。

---

## 模块一：企业微信群机器人推送集成 (WeChat Work Webhook)

通过企业微信群聊机器人，HR 可以一键将 AI 招聘助手生成的“招聘简报”或候选人新入库通知自动推送至指定的企业微信群。

### 1. 技术方案：企业微信群机器人 Webhook
企业微信群机器人提供了一个标准 HTTPS Webhook 接口，支持向群聊发送文本、Markdown、图片和卡片消息。

### 2. 后端服务端实现代码 (Node.js/Express)
您可以在工作台的后端服务 `server.ts` 中直接接入以下路由接口，实现一键推送：

```typescript
// server.ts /api/wechat/push 路由示例
import axios from "axios";

app.post("/api/wechat/push", async (req, res) => {
  const { content } = req.body;
  
  // 生产环境中，Webhook 地址应写在 .env 环境变量中
  const WECHAT_WEBHOOK_URL = process.env.WECHAT_WEBHOOK_URL; 
  
  if (!WECHAT_WEBHOOK_URL) {
    return res.status(400).json({ error: "企业微信群机器人 Webhook 地址未配置" });
  }

  try {
    const payload = {
      msgtype: "markdown",
      markdown: {
        content: content || "### 智聘 AI 招聘进展汇报\n今日无更新"
      }
    };

    const response = await axios.post(WECHAT_WEBHOOK_URL, payload);
    
    if (response.data.errcode === 0) {
      res.json({ success: true, message: "推送成功" });
    } else {
      res.status(500).json({ error: "企微返回错误", details: response.data });
    }
  } catch (error: any) {
    console.error("企微推送失败:", error);
    res.status(500).json({ error: "服务器通信异常", message: error.message });
  }
});
```

### 3. 企业微信群机器人配置步骤
1. 打开手机端或 PC 端企业微信，进入需要推送的**工作群**。
2. 点击群设置 -> **群机器人** -> **添加机器人**。
3. 命名为“智聘AI助手”，生成专属的 **Webhook URL** (包含 `key=xxxxx`)。
4. 将该 URL 配置到服务器的环境变量 `WECHAT_WEBHOOK_URL` 中即可开始调用。

---

## 模块二：腾讯文档（智能表格/收集表）双向同步集成

将智聘工作台中的候选人全流程台账数据，与腾讯文档（如智能表格 Smart Sheets）进行云端双向同步，方便高管或跨部门直接通过腾讯文档查阅。

### 1. 技术方案：腾讯文档开放平台 API (OAuth 2.0)
腾讯文档开放平台提供了丰富的智能表格 API（支持增、删、改、查、行列操作）。
- **认证方式**：采用 OAuth 2.0 授权码模式，获取 `access_token` 进行鉴权调用。
- **核心接口**：
  - 更新工作表行列数据：`POST https://docs.qq.com/open/api/v1/sheet/write`
  - 智能表格（Sheet）记录写入：`POST https://docs.qq.com/open/api/v2/smart/sheet/{sheetId}/records`

### 2. 候选人新入库自动同步到腾讯文档 (Node.js 实现)
每当 HR 在本工作台点击“确认入库”后，后端在写入本地数据库的同时，触发同步 API：

```typescript
// 伪代码：候选人入库同步腾讯文档
async function syncToTencentDocs(candidate: any) {
  const TENCENT_DOCS_APP_ID = process.env.TENCENT_DOCS_APP_ID;
  const TENCENT_DOCS_APP_SECRET = process.env.TENCENT_DOCS_APP_SECRET;
  const SHEET_ID = process.env.TENCENT_SHEET_ID; // 目标在线文档ID

  // 1. 获取腾讯文档 API 调用凭证 (Token)
  const tokenUrl = "https://docs.qq.com/oauth/v2/token";
  // 详情参见腾讯文档开发者文档鉴权流程获取 AccessToken

  // 2. 调用智能表格写入接口，追加候选人记录
  const writeUrl = `https://docs.qq.com/open/api/v2/smart/sheet/${SHEET_ID}/records`;
  const recordPayload = {
    records: [
      {
        fields: {
          "申请ID": candidate.id,
          "姓名": candidate.name,
          "岗位": candidate.jobTitle,
          "部门": candidate.department,
          "跟进HR": candidate.hrName,
          "流程状态": candidate.status,
          "最近结论": candidate.latestConclusion,
          "入库时间": new Date().toLocaleString()
        }
      }
    ]
  };

  try {
    const response = await axios.post(writeUrl, recordPayload, {
      headers: {
        "Authorization": `Bearer ${accessToken}`,
        "Content-Type": "application/json",
        "Client-Id": TENCENT_DOCS_APP_ID
      }
    });
    console.log("同步到腾讯文档成功:", response.data);
  } catch (error) {
    console.error("同步到腾讯文档失败:", error);
  }
}
```

### 3. 双向同步：腾讯文档数据反向同步回工作台
1. **方案一（定时轮询）**：工作台后端设置定时任务（Cron Job），每 10 分钟调用腾讯文档 `GET /smart/sheet/{sheetId}/records` 接口，拉取最新修改，更新本地内存数据库。
2. **方案二（Webhook 回调）**：在腾讯文档开放平台配置 Webhook 订阅事件（当文档被编辑时），腾讯文档服务器会自动向智聘工作台后端发送推送，触发本地同步。

---

## 模块三：生产环境架构部署推荐

针对“智聘 AI 招聘工作台”，在企业生产环境下落地，推荐以下高可靠架构设计：

```
+-------------------------------------------------------------+
|                     HR / 招聘官 浏览器前端                    |
|                (智能简历录入 / 全流程台账 / AI助手)           |
+------------------------------+------------------------------+
                               |
                               | (标准 HTTPS RESTful API)
                               v
+-------------------------------------------------------------+
|                    智聘 Express 业务服务端                  |
|          - 本地持久化缓存 DB / Drizzle SQL                   |
|          - 接入 Gemini 3.5 智能大模型服务接口                  |
+---------+--------------------+--------------------+---------+
          |                    |                    |
          | (Webhook 消息)      | (OAuth API 调用)    | (LLM SDK)
          v                    v                    v
+------------------+  +------------------+  +-----------------+
|  企业微信群机器人  |  |   腾讯智能文档   |  |   Gemini AI     |
|   (群聊简报通知)  |  |  (同步台账云盘)  |  |  (简历/洞察引擎)|
+------------------+  +------------------+  +-----------------+
```

### 环境变量配置指南
在生产环境部署时，请在服务器的 `.env` 中加入以下配置：
```bash
# Gemini 大模型 API
GEMINI_API_KEY="AI_Studio_API_Key"

# 企业微信推送配置
WECHAT_WEBHOOK_URL="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxx"

# 腾讯文档开放平台配置
TENCENT_DOCS_APP_ID="腾讯云开发者APP_ID"
TENCENT_DOCS_APP_SECRET="腾讯云开发者APP_SECRET"
TENCENT_SHEET_ID="在线智能表格SHEET_ID"
```

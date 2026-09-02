# 国网智策 Policy Copilot (sg-policy)

<div align="center">

**基于 Next.js 16 + LangGraph + CopilotKit v2 + RAGFlow 的电力政策知识库智能问答与决策辅助系统**

[特性概览](#-核心特性) • [环境准备](#-前置条件) • [配置指南](#-环境变量配置) • [快速启动](#-项目启动过程) • [架构说明](#-核心架构与技术栈) • [常见问题](#-常见问题排查)

</div>

---

## 📖 项目简介

**国网智策 Policy Copilot** 是一套面向电力能源、电价政策、电网数字化规划及企业规程咨询的智能助手。系统基于 **LangGraph Python Agent** 与 **CopilotKit v2** 构建，通过 **RAGFlow** 企业级知识库进行语义检索增强，具备事实精准溯源、原文即时预览、多轮对话状态隔离以及 A2UI 动态生成式交互能力。

---

## ✨ 核心特性

- ⚡ **RAG 语义检索增强**：采用轻量级中间件架构在 Agent 执行前自动检索 RAGFlow 知识库，智能注入精准事实上下文。
- 📌 **精准切片角标引用 (`[Fig. n]`)**：大模型在生成答案时规范标注切片来源，鼠标悬浮即可即时弹出切片原文、匹配置信度及所属文件。
- 📄 **原生物档在线预览与下载**：回答末尾自动聚合展示当前消息实际引用的参考文件胶囊，支持 DOCX、XLSX、PDF 等格式的在线极速原样预览及源文件下载。
- 🎨 **A2UI 动态生成式画板**：支持由大模型驱动动态生成电价结构图表、数字化项目预算表及政策全景看板。
- 🔄 **隔离式 AgentState 状态流**：后端将检索到的切片和聚合文档按每轮对话 ID 隔离存入 `AgentState.rag_citations`，确保多轮会话精准回溯、互不干扰。

---

## 🛠️ 前置条件

在启动项目之前，请确保您的本地开发环境满足以下要求：

1. **Node.js**：`18.0.0` 或更高版本（推荐 `Node.js 20+`）
2. **Python**：`3.10`、`3.11` 或 `3.12`
3. **uv**（推荐的现代 Python 快速包管理器）：
   ```bash
   # macOS / Linux 安装 uv
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Windows (PowerShell) 安装 uv
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```
4. **RAGFlow 知识库实例**：本地 Docker 运行或云端可访问的 RAGFlow 服务，并已创建包含政策文档的 Dataset（知识库）。
5. **大语言模型 API Key**：OpenAI API Key，或兼容 OpenAI 格式的大模型 API（如阿里云 DashScope Qwen、DeepSeek 等）。

---

## ⚙️ 环境变量配置

在项目根目录下创建并配置 `.env` 文件：

```bash
cp .env.example .env
```

打开 `.env` 文件，按需填写以下核心配置项：

```env
# ==========================================
# 1. 大语言模型配置 (OpenAI / Qwen / DeepSeek)
# ==========================================
OPENAI_API_KEY=sk-your-model-api-key-here
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_MODEL=qwen-plus-latest

# ==========================================
# 2. RAGFlow 知识库服务配置
# ==========================================
# RAGFlow API 基础地址 (本地默认 http://localhost 或云端 IP:端口)
RAGFLOW_API_URL=http://localhost/api/v1
# RAGFlow API Key (在 RAGFlow 控制台 -> API Keys 中生成)
RAGFLOW_API_KEY=ragflow-your-api-key-here
# 默认绑定的 Dataset ID (知识库 ID，多个逗号隔开)
RAGFLOW_DATASET_IDS=d4d0e9c6a05c11f199bf45be651e52f0

# ==========================================
# 3. Agent 端口与服务地址
# ==========================================
AGENT_URL=http://localhost:8123
LANGGRAPH_DEPLOYMENT_URL=http://localhost:8123
PORT=3000
```

---

## 🚀 项目启动过程

### 第一步：安装前端与后端依赖

在项目根目录下执行包管理器安装命令（`postinstall` 钩子会自动使用 `uv` 初始化 Python 虚拟环境并安装 Agent 依赖）：

```bash
# 使用 npm 安装
npm install

# 或者使用 pnpm / yarn / bun
# pnpm install
# yarn install
# bun install
```

> **提示**：如果需要单独为 Python Agent 初始化环境，可执行：
> ```bash
> cd agent && uv sync && cd ..
> ```

---

### 第二步：启动开发环境

#### 方式一：一键并发启动前端与后端 Agent（推荐）

直接在根目录下运行：

```bash
npm run dev
```

该命令会同时拉起：
- 🌐 **前端 UI 服务**：`http://localhost:3000`（Next.js 16 + Turbopack）
- 🤖 **后端 Agent 服务**：`http://localhost:8123`（LangGraph CLI 开发服务器）

---

#### 方式二：分终端独立启动（推荐调试时使用）

如果您希望分别观察前端和后端的详细日志输出，可在两个独立终端窗口中分别运行：

**终端 1（启动后端 LangGraph Agent）：**
```bash
npm run dev:agent
```
> 后端服务将在 `http://localhost:8123` 启动并自动监听 Python 源码变动热重载。

**终端 2（启动前端 Next.js UI）：**
```bash
npm run dev:ui
```
> 前端界面将在 `http://localhost:3000` 启动。

---

### 第三步：访问与体验系统

打开浏览器访问：
👉 **[http://localhost:3000](http://localhost:3000)**

您可以尝试咨询各类电力政策与业务需求，例如：
- *“请介绍北京市第四监管周期输配电价政策及分时标准。”*
- *“2027年国网北京数字化数据工程项目的投资预算是多少？”*
- *“中华人民共和国能源法在节约能源方面有哪些规定？”*

系统将自动检索 RAGFlow 知识库，生成带 `[Fig. n]` 切片角标的严谨回答，并在正文末尾附带参考来源政策文档胶囊，点击即可原样在线预览。

---

## 📁 常用开发脚本说明

| 脚本命令 | 功能说明 |
| :--- | :--- |
| `npm run dev` | 并发启动前端 UI（3000 端口）和后端 Agent（8123 端口） |
| `npm run dev:ui` | 仅启动 Next.js 前端应用（基于 Turbopack） |
| `npm run dev:agent` | 仅启动 LangGraph Python Agent 服务 |
| `npm run build` | 编译构建生产环境前端应用 Bundle |
| `npm run start` | 以生产模式运行前端应用 |
| `npm run install:agent` | 重新安装并同步 Python Agent 虚拟环境及依赖 |

---

## 🏗️ 核心架构与技术栈

```
sg-policy/
├── agent/                         # LangGraph Python 后端 Agent
│   ├── main.py                    # Agent 核心图装配、模型与系统提示词
│   ├── src/
│   │   ├── rag_middleware.py      # RAGFlow 前置切片检索与状态注入中间件
│   │   ├── ragflow_tool.py        # RAGFlow API 客户端与数学计算工具
│   │   ├── todos.py               # AgentState 定义（包含 rag_citations）
│   │   └── a2ui_dynamic_schema.py # A2UI 动态生成式 UI 生成器
│   └── pyproject.toml             # Python 依赖配置
│
├── src/                           # Next.js 16 前端应用
│   ├── app/
│   │   ├── page.tsx               # 主工作台页面
│   │   └── api/
│   │       ├── copilotkit/        # CopilotKit 运行时 API 路由
│   │       └── documents/         # RAGFlow 原生物档下载与预览代理
│   ├── components/
│   │   ├── citation/              # 引用切片与文档预览组件体系
│   │   │   ├── citation-assistant-message.tsx # 定制化消息与来源渲染
│   │   │   ├── citation-badge.tsx             # [Fig. n] 悬浮切片卡片
│   │   │   ├── document-pill.tsx              # 底部文档胶囊按钮
│   │   │   └── file-previewer.tsx             # DOCX/XLSX/PDF 文件预览模态框
│   │   └── example-canvas/        # 右侧政策库与数据看板画板
│   └── lib/
│       └── citation-service.ts    # 客户端引用数据缓存与工具函数
│
└── package.json                   # 工程依赖与启动脚本
```

---

## ❓ 常见问题排查

### 1. 启动时提示 `8123` 端口被占用？
- **原因**：之前的 LangGraph 进程未完全退出。
- **解决办法**：
  ```bash
  # 查找并释放 8123 端口
  lsof -i :8123
  pkill -f "langgraph"
  ```

### 2. 前端提问后提示 `Failed to fetch from agent`？
- 确认后端 `npm run dev:agent` 是否正常运行在 `http://localhost:8123`；
- 检查 `.env` 文件中的 `AGENT_URL` 是否正确配置为 `http://localhost:8123`。

### 3. 文档在线预览加载失败？
- 确认 `.env` 中的 `RAGFLOW_API_URL` 和 `RAGFLOW_API_KEY` 是否正确且有效；
- 确认 RAGFlow 服务正常运行且该文件在对应的 Dataset 中未被删除。

---

## 📄 开源许可

本项目遵循 MIT 开源许可协议。

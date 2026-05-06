<div align="center">

<img src="docs/images/banner.svg" alt="OpenArma Banner" width="100%">

# OpenArma

**AI 军事指挥官 — 可配置的多智能体平台，以 Arma Reforger 为首个战场**

[![GitHub Stars](https://img.shields.io/github/stars/chenhaha99/OpenArma?style=flat-square)](https://github.com/chenhaha99/OpenArma/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/chenhaha99/OpenArma?style=flat-square)](https://github.com/chenhaha99/OpenArma/network)
[![GitHub Issues](https://img.shields.io/github/issues/chenhaha99/OpenArma?style=flat-square)](https://github.com/chenhaha99/OpenArma/issues)
[![GitHub License](https://img.shields.io/github/license/chenhaha99/OpenArma?style=flat-square)](https://github.com/chenhaha99/OpenArma/blob/main/LICENSE)

[中文文档](#简体中文) | [English](#english)

</div>

---

<a id="简体中文"></a>

<div align="center">
<img src="docs/images/intro.png" alt="OpenArma 项目介绍" width="800">
</div>

## ⚡ 项目概述

假设你设计了一个 AI 军事助手，你很难让它去真的打一场仗来演示效果。

OpenArma 解决了这个问题 — 通过 **Arma Reforger**（一款拥有军事沙盘式环境的游戏），让 AI 指挥官在真实的战术环境中做出决策、下达命令、观察结果。你可以像"红色警戒"一样宏观控制，也可以扮演其中一名士兵，亲身体验 AI 的指挥效果。

> 始于战场，但不止于战场。OpenArma 的底层是一个通用的多智能体平台 — 你可以创建项目、配置智能体、接入自己的 LLM、设计多智能体协作拓扑。军事指挥只是第一个应用场景。

<div align="center">

▶️ **演示视频** | [Bilibili (中文)](https://www.bilibili.com/video/BV1tuRFBUESe) | [YouTube (English)](https://www.youtube.com/watch?v=S348nJ6qFfU)

</div>

<div align="center">

🌐 **在线演示** | [openarma.com](https://openarma.com) | [对话分享示例](https://openarma.com/shared/fa508f0d-5786-4c21-84b3-57510f2c1573)

> ⚠️ 在线演示服务器将于 **2026 年 5 月 20 日**到期，届时如需体验请自行部署。

</div>

## 🎯 一场完整的 AI 指挥演示是怎样的？

### 1. 设计你的 AI 指挥官

在 Web 界面创建一个智能体，赋予它指挥官的角色。你可以自定义它的系统提示词、行为规则、可用工具。

比如在测试中我们发现：AI 在遭遇敌人时，总是优先调用火炮进行打击 — 就像那位英国教授的论文里说的，21 场模拟战争中有 20 场 AI 都使用了核弹。AI 把这些武器视为效率极高的工具，而不是人类眼中的"最后手段"。所以我们可以通过规则限制 AI 的武器使用权，引导它执行包抄、侧翼迂回等战术。

### 2. 配置对话与阵营

在项目中新建一个对话，为不同阵营分配 AI 或人类控制：

- **AI vs 人类**：AI 指挥一方，你操控另一方
- **AI vs AI**：两个独立的 AI 指挥官对抗，各自只能看到己方侦察到的信息（**战争迷雾**）

你也可以将同一个智能体绑定不同的大模型，分别指挥两个阵营 — 实现同等条件下不同模型的对抗测试。

每个对话需要设置**任务目标**和**作战区域**。AI 指挥官围绕目标做出所有决策。

### 3. AI 如何感知战场？

这是项目中最核心的设计之一：**不是把所有信息都告诉 AI，而是给它工具，让它自己决定需要什么。**

任务开始时，AI 会收到一份简报 — 基础的地形概况和兵力部署。如果它想了解更多：

- 想知道某个区域的建筑分布？调用工具，输入坐标，获取详细信息
- 想了解某条路线的隐蔽性？工具会告诉它植被覆盖率、地形遮蔽情况
- 想评估进攻路线？路径规划工具会综合通行性、掩蔽度、坡度给出建议

就像真正的指挥官一样：你不会一开始就阅读所有情报，而是根据需要去调取。

### 4. 地图：AI 理解世界的方式

人类擅长读图，AI 擅长读文字。我们的方案是：把地图信息按区域划分成六角格，将每个格子内的植被、建筑、地势转化为文字描述，然后向量化。

这些信息的源头非常精细 — 每棵树的坐标和大小、每栋建筑的朝向和尺寸、每条道路的宽度和路径。基于这些原始数据，系统可以生成：

- **植被密度图** — 哪里是密林，哪里是开阔地
- **建筑分布** — 城镇还是村庄，驻防价值如何
- **通行性分析** — 坦克能不能过，步兵走这条路要多久
- **隐蔽性评估** — 进攻选隐蔽路线，防守重点巡逻隐蔽区域
- **通视域分析** — 从这个山头能看到多远
- 更多专题图层...

### 5. 多智能体参谋部

单个 AI 指挥官一个人干所有活，效果有限。所以我们设计了多智能体协作：

你可以搭建一个"参谋部" — 比如一个植被信息参谋负责提供原始地理数据，一个路径参谋善于多角度制定路线，一个假想敌参谋会模拟敌方可能的计划。他们各自分析后，汇总给参谋长，参谋长综合所有信息做出最终决策。

整个参谋部的结构可以完全自定义：谁和谁讨论、讨论几轮、是相互辩论还是逐级汇报 — 通过可视化的 DAG 拓扑编辑器拖拽构建。

### 6. 从经验中学习

任务结束后，AI 会像人类一样进行复盘：

- 如果伤亡率高，分析哪个阶段的决策可能导致了伤亡
- 如果任务失败，记录失败原因和建议

这些经验存入知识库，向量化。下一场任务时，AI 可以检索到类似情况下的历史教训。经验库还会统计每种决策的成功/失败次数 — 某个战术多次使用效果不好，AI 就会自动规避。

**两套知识库**：一套客观的地图数据（每次根据任务目标获取不同信息），一套跨任务的经验库（让 AI 学习历史教训）。

## 🚀 核心功能

### 平台能力

| 功能 | 说明 |
|:---|:---|
| 多智能体协作 | 可视化 DAG 拓扑编辑器，自定义协作流程（讨论 / 汇报 / 投票） |
| 知识库 (RAG) | 文档上传 → 向量化 → 语义检索，按需绑定到智能体 |
| LLM 服务商管理 | 自带 API Key，预设 DeepSeek / OpenAI / Anthropic / Gemini 等 10+ 服务商 |
| 工具调用 | 内置工具 + MCP 服务器集成，智能体自主决定何时调用 |
| 对话分支 | 编辑重发、重新生成、分支导航 |
| 资源系统 | 智能体 / 知识库 / 拓扑 — 全局资源，支持私有 / 公开 / 官方 |
| 社区展示 | 浏览和一键克隆公开资源 |
| 用量追踪 | Token 消耗、费用估算、调用明细 |

### Arma Reforger 集成

| 功能 | 说明 |
|:---|:---|
| AI vs 人类 | AI 指挥一方，人类操控另一方 |
| AI vs AI | 两个独立 AI 指挥官，战争迷雾 |
| Web 控制面板 | 启停、阵营配置、决策间隔 — 全部浏览器操作 |
| 地形感知 | H3 六角格分析、A* 路径规划、多种专题图层 |
| 地图系统 | 瓦片式查看器、六位军用坐标、山体阴影 |
| 战斗回放 | 逐帧复盘，还原任务全过程 |

### Arma 模组仓库

| 模组 | 说明 | 仓库 |
|:---|:---|:---|
| **OpenArma Mod Main** | 核心模组 — AI 指挥官运行时 | [GitHub](https://github.com/chenhaha99/OpenArma-Mod-Main) |
| **OpenArma Mod MapExporter** | Workbench 地图数据导出 | [GitHub](https://github.com/chenhaha99/OpenArma-Mod-MapExporter) |
| **OpenArma Mod MapScanner** | 游戏内地图扫描 | [GitHub](https://github.com/chenhaha99/OpenArma-Mod-MapScanner) |

## 🏗️ 系统架构

```
┌──────────────────────────────────────────────────────────┐
│                     Next.js 前端                          │
│  项目管理 · 对话 · 智能体配置 · 拓扑编辑器 · 知识库       │
│  LLM 管理 · 用量仪表盘 · 管理后台 · 国际化 · 暗色模式    │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────┴─────────────────────────────────┐
│               FastAPI 后端 (基于 fba)                      │
│  认证 · 插件 · 异步任务 · SSE 流式 · 可观测性              │
├──────────────────────────────────────────────────────────┤
│  对话引擎 (LangGraph + LiteLLM)                           │
│  单/多智能体 · DAG 拓扑 · 工具调用 · RAG 检索             │
├──────────────────────────────────────────────────────────┤
│  Arma 集成层 (Open API)                                    │
│  指挥端点 · 战斗状态机 · 消息队列 · 地图工具               │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────┴─────────────────────────────────┐
│  PostgreSQL · Redis · RabbitMQ · Qdrant · MinIO           │
│  Grafana · Prometheus · Tempo · Loki                      │
└──────────────────────────────────────────────────────────┘
```

## 🛠️ 技术栈

| 层级 | 技术 |
|:---|:---|
| 前端 | Next.js 16 · React 19 · shadcn/ui · Tailwind CSS 4 · Zustand · React Flow |
| 后端 | FastAPI (fba) · SQLAlchemy 2 · Pydantic v2 · Celery · Alembic |
| AI 引擎 | LangGraph · LiteLLM · Qdrant |
| 数据库 | PostgreSQL 16 (pgvector) · Redis · RabbitMQ |
| 存储 | MinIO (S3 兼容) |
| 可观测性 | Grafana · Prometheus · Tempo · Loki |
| 部署 | Docker Compose · Nginx |

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+ & pnpm
- PostgreSQL 16+（pgvector 扩展）
- Redis
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

### 后端

```bash
uv sync
cp backend/.env.example backend/.env
# 编辑 .env，填入数据库配置
fba init --auto
fba run
```

### 前端

```bash
cd frontend
pnpm install
pnpm dev
```

### Docker 部署

```bash
cp deploy/backend/docker-compose/.env.server.example deploy/backend/docker-compose/.env.server
# 编辑 .env.server
docker compose build
docker compose up -d
```

详细部署文档参见 [DEPLOY.md](./DEPLOY.md)。

## 📁 项目结构

```
openarma/
├── backend/                    # FastAPI 后端
│   └── app/
│       ├── agent/              # 智能体配置
│       ├── conversation/       # 对话引擎 (LangGraph)
│       ├── knowledge/          # 知识库 + RAG
│       ├── llm/                # LLM 服务商
│       ├── map/                # 地图数据 + 地形分析
│       ├── open/               # Arma Open API
│       ├── topology/           # DAG 拓扑
│       └── ...
├── frontend/                   # Next.js 前端
├── deploy/                     # 部署配置
├── docker-compose.yml
└── pyproject.toml
```

## 🤝 贡献指南

欢迎所有形式的贡献！

1. **Fork** 本仓库
2. **创建分支**：`git checkout -b feature/your-feature`
3. **提交更改**：`git commit -m '添加 xxx 功能'`
4. **推送 & 创建 Pull Request**

## ⚠️ 免责声明

本项目仅用于学术研究和技术演示目的。项目中涉及的军事场景均在虚拟游戏环境中模拟，不涉及任何真实军事应用。使用者应遵守所在地区的法律法规。

## 📄 许可证

本项目基于 [MIT License](LICENSE) 开源。

## 🙏 致谢

- [fastapi_best_architecture](https://github.com/fastapi-practices/fastapi_best_architecture) — 后端基础框架
- [LINUX DO](https://linux.do/) — 社区支持与交流

---

<a id="english"></a>

<div align="center">

# OpenArma

**AI Military Commander — A configurable multi-agent platform with Arma Reforger as the first battlefield.**

[中文文档](#简体中文) | [English](#english)

</div>

## ⚡ Overview

Imagine you've built an AI military assistant — how do you demonstrate it? You can't exactly send it to a real battlefield.

OpenArma solves this by connecting to **Arma Reforger**, a military sandbox game. The AI commander observes the battlefield, makes tactical decisions, and issues orders to virtual troops in real-time. You can watch from above like a strategy game, or drop in as one of the soldiers to experience the AI's commands firsthand.

Under the hood, OpenArma is a general-purpose **multi-agent platform** — create projects, configure agents with custom prompts/tools/knowledge, connect your own LLMs, and design collaboration topologies. Military command is just the first application.

<div align="center">

▶️ **Demo Videos** | [Bilibili (中文)](https://www.bilibili.com/video/BV1tuRFBUESe) | [YouTube (English)](https://www.youtube.com/watch?v=S348nJ6qFfU)

🌐 **Live Demo** | [openarma.com](https://openarma.com) | [Shared conversation example](https://openarma.com/shared/fa508f0d-5786-4c21-84b3-57510f2c1573)

> ⚠️ The demo server expires on **May 20, 2026**. After that, please deploy your own instance to try it out.

</div>

## 🎯 How Does It Work?

**Design your AI commander** — Create an agent with custom system prompts, behavior rules, and tools. Discovered that AI always calls in artillery strikes? Add rules to restrict weapon usage and encourage flanking maneuvers.

**Set up the battle** — AI vs Human, or AI vs AI with fog of war. Each side only sees what their own scouts detect. You can even pit different LLM models against each other under identical conditions.

**Let AI decide what it needs** — Instead of dumping all information on the AI, we give it tools. It decides when to query building layouts, check terrain concealment, or plan routes. Just like a real commander requesting intelligence.

**Learn from experience** — After each mission, the AI reviews outcomes: what worked, what caused casualties, which decisions to avoid. These lessons are stored in a vector knowledge base for future missions.

## 🚀 Key Features

| Category | Features |
|:---|:---|
| **Platform** | Multi-agent collaboration · Visual DAG topology editor · RAG knowledge base · 10+ LLM providers · MCP tool integration · Conversation branching · Usage tracking |
| **Arma Integration** | AI vs Human / AI vs AI · Fog of war · Web control panel · H3 terrain analysis · A* pathfinding · Thematic map layers · Military grid coordinates |

### Arma Mod Repositories

| Mod | Description | Repository |
|:---|:---|:---|
| **Main** | Core mod — AI commander runtime | [GitHub](https://github.com/chenhaha99/OpenArma-Mod-Main) |
| **MapExporter** | Workbench map data export | [GitHub](https://github.com/chenhaha99/OpenArma-Mod-MapExporter) |
| **MapScanner** | In-game map scanning | [GitHub](https://github.com/chenhaha99/OpenArma-Mod-MapScanner) |

## 🛠️ Tech Stack

| Layer | Technology |
|:---|:---|
| Frontend | Next.js 16 · React 19 · shadcn/ui · Tailwind CSS 4 · Zustand · React Flow |
| Backend | FastAPI (fba) · SQLAlchemy 2 · Pydantic v2 · Celery · Alembic |
| AI Engine | LangGraph · LiteLLM · Qdrant |
| Database | PostgreSQL 16 (pgvector) · Redis · RabbitMQ |
| Storage | MinIO (S3-compatible) |
| Deployment | Docker Compose · Nginx |

## 🚀 Quick Start

### Backend

```bash
uv sync
cp backend/.env.example backend/.env
# Edit .env with your database config
fba init --auto
fba run
```

### Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

### Docker

```bash
cp deploy/backend/docker-compose/.env.server.example deploy/backend/docker-compose/.env.server
# Edit .env.server with production credentials
docker compose build
docker compose up -d
```

## ⚠️ Disclaimer

This project is for academic research and technical demonstration only. All military scenarios are simulated in a virtual game environment and involve no real-world military applications.

## 📄 License

[MIT License](LICENSE)

## 🙏 Acknowledgments

- [fastapi_best_architecture](https://github.com/fastapi-practices/fastapi_best_architecture) — Backend foundation
- [LINUX DO](https://linux.do/) — Community support

<p align="center">
  <img src="./logo/paper2agent_logo.png" alt="Paper2Agent Logo" width="600px" />
</p>

# Paper2Agent: Reimagining Papers As AI Agents

## 📖 Overview
`Paper2Agent` is a multi-agent AI system that automatically transforms research papers into interactive AI agents with minimal human input. Explore [demos](#-demos) of Paper2Agent-generated agents, or try it yourself at [paper2agent.ai](https://paper2agent.ai).

Paper2Agent coordinates parallel specialist agents to turn scientific papers into reliable MCP servers and skills.

## 🚀 Quick Start

### Basic Usage

The simplest way to use Paper2Agent is to ask your coding agent (Claude Code, Codex, etc.) to install the paper2agent skill, then agentify a paper alongside its code repository.

```text
Read https://github.com/jmiao24/Paper2Agent and install the paper2agent skill
from skills/paper2agent for this coding agent.

Use the paper2agent skill to agentify this paper and its associated files,
alongside its code repository if available. Follow the skill instructions
for the workflow, verification, and final delivery.

Paper and associated files: <PAPER_URL_OR_LOCAL_FILES>
Code repository (if available): <GITHUB_URL_OR_LOCAL_PATH>
Output directory: <PROJECT_DIR>
```

If the skill does not appear after installation, restart your coding agent. For manual installation, see [Installation & Setup](#installation).

See the [skill instructions](skills/paper2agent/SKILL.md) for supported inputs, workflows, and deliverables.

### Advanced Usage

#### Targeted Tasks or Tutorials

Specify the scientific tasks, tutorial title, or source URL to focus on:

```text
Use the paper2agent skill to convert <GITHUB_URL> into MCP tools in <PROJECT_DIR>.
Focus on <TASKS, TUTORIAL_TITLE, or SOURCE_URL>.
```

#### Repository with API Key

Make credentials available through your host's secret mechanism or process environment, then tell the agent the variable name:

```text
Use the paper2agent skill to convert <GITHUB_URL> into MCP tools in <PROJECT_DIR>.
Read the required API key from the environment variable <VARIABLE_NAME>.
```

Credentials stay outside generated code, notebooks, reports, and the delivered ZIP.

### Examples

The examples below use Claude Code's `/paper2agent` invocation. In Codex, replace it with `$paper2agent`.

#### TISSUE Agent

Create an AI agent from the [TISSUE](https://github.com/sunericd/TISSUE) research paper codebase for uncertainty-calibrated single-cell spatial transcriptomics analysis:

```text
/paper2agent Convert https://github.com/sunericd/TISSUE into tested MCP tools in TISSUE_Agent.
```

#### Scanpy Agent for Preprocessing and Clustering

Create an AI agent from the [Scanpy](https://github.com/scverse/scanpy) research paper codebase for single-cell analysis preprocessing and clustering:

```text
/paper2agent Convert https://github.com/scverse/scanpy into tested MCP tools in Scanpy_Agent.
Focus on the "Preprocessing and clustering" tutorial.
```

You can also provide a tutorial URL:

```text
/paper2agent Convert https://github.com/scverse/scanpy into tested MCP tools in Scanpy_Agent.
Focus on https://github.com/scverse/scanpy/blob/main/docs/tutorials/basics/clustering.ipynb.
```

#### AlphaGenome Agent

Create an AI agent from the [AlphaGenome](https://github.com/google-deepmind/alphagenome) research paper codebase for genomic data interpretation:

```text
/paper2agent Convert https://github.com/google-deepmind/alphagenome into tested MCP tools in AlphaGenome_Agent.
Read the API key from the environment variable ALPHAGENOME_API_KEY.
```

<a id="installation"></a>

## ⚙️ Installation & Setup

### Prerequisites

- **Coding-agent host:** A host with skill support, shell access, and parallel subagent spawning enabled. The coordinator launches specialists and fresh verifier agents through the host.
- **Runtime access:** Python and Git, plus any R, native CLI, data, API, or GPU requirements of the selected repository. The skill prepares isolated project environments and records tested versions.

### Manual Installation Steps

To have your coding agent install the skill, use the [Quick Start](#-quick-start) prompt. To install it yourself, follow the steps below.

1. **Clone the Paper2Agent repository**

   ```bash
   git clone https://github.com/jmiao24/Paper2Agent.git
   cd Paper2Agent
   ```

2. **Install the entire skill folder for your host**

   Choose the command for your host. Copy the entire folder, including all subdirectories and supporting files.

   **Claude Code** — personal skill location from the [Claude Code skills documentation](https://code.claude.com/docs/en/skills):

   ```bash
   mkdir -p "$HOME/.claude/skills/paper2agent"
   cp -R skills/paper2agent/. "$HOME/.claude/skills/paper2agent/"
   ```

   **Codex** — personal skill location from the [official OpenAI skills documentation](https://learn.chatgpt.com/docs/build-skills):

   ```bash
   mkdir -p "$HOME/.agents/skills/paper2agent"
   cp -R skills/paper2agent/. "$HOME/.agents/skills/paper2agent/"
   ```

3. **Start your coding agent in your analysis workspace**

   Open Claude Code or Codex in the directory where you want to work, then use the [Quick Start](#-quick-start) prompt. If the skill does not appear, restart the coding agent. The skill installs the generated server's dependencies in its project environment during conversion.

## 🤖 How to Create a Paper Agent?

Connect the generated Paper MCP server to an AI coding agent, such as [Claude Code](https://www.anthropic.com/claude-code), Codex, or the [Google Gemini CLI](https://google-gemini.github.io/gemini-cli/), to use its scientific tools in conversation.

### Connect a Generated Local MCP Server

Extract the delivered ZIP and follow its `USAGE.md` to install dependencies and configure your MCP client. The instructions include the tested interpreter, server entry point, required environment variables, and supported platforms.

To have the coding agent configure the connection, explicitly request it after conversion:

```text
Connect the generated MCP server to my coding-agent client using its USAGE.md.
```

### Connect a Remote MCP Server Hosted on Hugging Face

You can also use an existing server from [Connectable Paper MCP Servers](#-connectable-paper-mcp-servers). Open the hosted service's instructions for its MCP endpoint, transport, and authentication requirements.

For an HTTP endpoint in Claude Code, follow the [MCP connection documentation](https://code.claude.com/docs/en/mcp):

```bash
claude mcp add --transport http <MCP_NAME> <MCP_ENDPOINT_URL>
```

For example, the [hosted AlphaGenome MCP server](https://Paper2Agent-alphagenome-mcp.hf.space) can provide tools for genomic data interpretation. Once connected, you can input a query like:

```text
Analyze heart gene expression data with AlphaGenome MCP to identify the causal gene
for the variant chr11:116837649:T>G, associated with Hypoalphalipoproteinemia.
```

### Verification

In Claude Code, check the server's connection status with:

```bash
claude mcp list
```

Or use `/mcp` inside Claude Code. A successful connection should appear in the server list; use a tool call to confirm the scientific workflow works with your inputs. The screenshot below shows the AlphaGenome MCP server connected in Claude Code.

<img width="620" alt="Claude Code showing the AlphaGenome MCP server connected" src="assets/claude-code-mcp.png" />

## 🎬 Demos
Below, we showcase demos of AI agents created by Paper2Agent, illustrating how each agent applies the tools from its source paper to tackle scientific tasks.
### 🧬 AlphaGenome Agent for Genomic Data Interpretation
Example query:
```
Analyze heart gene expression data with AlphaGenome MCP to identify the causal gene
for the variant chr11:116837649:T>G, associated with Hypoalphalipoproteinemia.
```

https://github.com/user-attachments/assets/34aad25b-42b3-4feb-b418-db31066e7f7b

### 🗺️ TISSUE Agent for Uncertainty-Aware Spatial Transcriptomics Analysis
Example query:
```
Calculate the 95% prediction interval for the spatial gene expression prediction of gene Acta2 using TISSUE MCP.

This is my data:
Spatial count matrix: Spatial_count.txt
Spatial locations: Locations.txt
scRNA-seq count matrix: scRNA_count.txt
```

https://github.com/user-attachments/assets/2c8f6368-fa99-4e6e-b7b5-acc12f741655

### 🧫 Scanpy Agent for Single-Cell Data Preprocessing
Example query:
```
Use Scanpy MCP to preprocess and cluster the single-cell dataset pbmc_all.h5ad.
```

## 🔗 Connectable Paper MCP Servers
* AlphaGenome: https://Paper2Agent-alphagenome-mcp.hf.space
* Scanpy: https://Paper2Agent-scanpy-mcp.hf.space
* TISSUE: https://Paper2Agent-tissue-mcp.hf.space

## 📚 Citation
```
@article{miao2026paper2agent,
  title={Reimagining research papers as interactive and reliable {AI} agents},
  author={Miao, Jiacheng and Davis, Joe R. and Zhang, Yaohui and Pritchard, Jonathan K. and Zou, James},
  journal={Nature},
  year={2026},
  doi={10.1038/s41586-026-11044-y},
  url={https://www.nature.com/articles/s41586-026-11044-y}
}
```



---

# GSGP-BENCH 部署与运维（本 fork 线记录）

> 以上为上游 Paper2Agent 原文。以下记录本 fork（`origin = hhtttyy/GSGP-BENCH`，`upstream = jmiao24/Paper2Agent`）的两条并行部署线：**GitHub + Cloudflare Workers（海外）** 与 **阿里云 ECS（国内）**。国内线不改动 GitHub/Cloudflare 线的任何配置；本节即国内线的使用流程存档。

## 0. 两条部署线总览

| 线 | 入口 | 开屏双螺旋 | AI 解读/预审 | 更新触发 |
| --- | --- | --- | --- | --- |
| GitHub + Cloudflare Workers | `https://<worker>.<subdomain>.workers.dev`（见 Dashboard） | 全断点 three.js 慢旋（jsdelivr CDN） | Worker `/api/analyze`、`/api/prospective`（Worker Secret 密钥） | push `main` → Workers Builds 自动部署 |
| 阿里云 ECS（国内） | `http://101.200.149.60/gsgp/`（根路径 301 到前缀） | 混合：移动静态帧 / 桌面 three.js 慢旋（本地 vendor） | 回环 `gsgp-api` 127.0.0.1:8787（env 600 密钥），nginx 反代 `/gsgp/api/` | 手动四步更新（见 1.3） |

两线共用同一份前端源 `site/` 与同一套证据账本 `site/data/`；国内线发布产物为 `deploy-cn/`（源）与 `deploy-cn.zip`（产物包）。

## 1. 阿里云 ECS 线（国内）

### 1.1 资源与前置

- ECS：`ecs.e-c1m1.large`（2vCPU 2GiB、3M 固定带宽、40G ESSD Entry），Alibaba Cloud Linux 4，华北 2；公网 IP 即入口，无域名、无备案需求。
- 安全组：TCP 80 允许 0.0.0.0/0；TCP 22 暂全开（建议从 `echo $SSH_CLIENT` 取真实来源后收紧 /32，或改密钥登录）。
- 镜像虽为宝塔市场镜像，但**面板停用、走系统 nginx**（`/etc/init.d/bt stop` + 取消自启）；dnf 对 nginx 有镜像预置 exclude，安装需 `--disableexcludes=all` 单次绕过。
- 2G 内存可选加 2G swap（`fallocate/mkswap/swapon` + fstab）。

### 1.2 首次部署（`deploy-cn/setup.sh`，使用者本人运行）

脚本行为公告：`dnf install -y --disableexcludes=all nginx`（唯一安装项）→ 从 registry.npmmirror.com 拉 three.js r160 三文件到 `vendor/`（备源 jsdelivr）→ 备份并替换 nginx 主配置、写入 `conf.d/gsgp.conf` → 创建 `/etc/gsgp-bench.env`（**密钥静默粘贴、chmod 600、不入库**）→ 安装 `gsgp-api` systemd 服务（仅回环 8787）→ firewalld 条件放行 → 本地验收。
路径约定：站点根 `/www/wwwroot/gsgp/`；nginx `root /www/wwwroot` + `location /gsgp/`；AI 代码 `/opt/gsgp-api/server.py`；存活 watchdog `gsgp-api-watchdog.timer` 每 60s 判活（405 探针，不发付费调用）。

### 1.3 版本更新标准四步（漏第 3 步＝线上不变）

1. SFTP 上传新 `deploy-cn.zip` 到 `/root/`；`stat -c %s` 与发布字节数核对。
2. `cd /root && unzip -o deploy-cn.zip >/dev/null`（只更新 /root/deploy-cn）。
3. **同步到站点根**：`\cp -a /root/deploy-cn/www/. /www/wwwroot/gsgp/`（纯静态覆盖，无需 reload/restart；多站点同步到对应 `/www/wwwroot/<name>/`）。
4. 验收：`bash /root/deploy-cn/verify-cn.sh http://127.0.0.1 --with-ai` 全 PASS + 双端目检。
nginx/systemd 配置类改动才需要 `nginx -t && systemctl reload nginx` / `daemon-reload + restart`。

### 1.4 验收与观测

- `verify-cn.sh`：根/旧链 301、前缀路由 200、静态帧标记、混合 importmap 标记、vendor 200、gzip、`/gsgp/api/analyze|prospective` 200、GET 405。
- 错误三层可见：页面红字原因 → `journalctl -u gsgp-api -f` / `--since "-24h" -o cat | grep -E "upstream_error|failed"`（行含 status/class/detail，不含密钥）→ `bash /opt/gsgp-api/api-status.sh`（状态、NRestarts、watchdog、24h 六类错误计数、成功耗时；`--probe` 才发真实调用）。
- 错误码：`AI_BALANCE_INSUFFICIENT`（402/arrearage/余额/欠费→充值）、`AI_AUTH_INVALID`（401→查 env）、`AI_RATE_LIMITED`（429/quota）、`AI_TIMEOUT`（`AI_TIMEOUT_SEC` 默认 60）、`AI_CONNECT_FAILED`、`AI_UPSTREAM_ERROR`、`AI_EMPTY_RESPONSE`。预审失败自动回退允许清单模板并注明原因，记录保持待认证。

### 1.5 多站点扩展（无域名 ⇒ 路径前缀，共用 80）

`bash add-site.sh <name> [api-port]`：建 `/www/wwwroot/<name>/`、生成 `conf.d/sites/<name>.conf`（被主 server include）、可选独立 AI 实例（`/opt/<name>-api/` + `/etc/<name>-bench.env` + `<name>-api.service`，回环端口预留 8788–8797）、登记 `/www/wwwroot/SITES.md`。无需新开安全组端口。bench 以 `../api/` 相对站点根调用，各站反代自己的回环端口，天然隔离。

### 1.6 回滚与常见坑

- 回滚绳：`/etc/nginx/nginx.conf.bak-gsgp`、`conf.d/gsgp.conf.bak-root`、`/www/wwwroot/gsgp/index.html.bak-static`（纯静态首页）。
- 坑：root 的 `cp` 别名带 `-i`（覆盖询问，用 `\cp` 绕过）；`unzip` 不等于上线（必须第 3 步同步）；旧前端绝对路径 `/api/` 遇 301 会 **POST 变 GET** 得 405「请使用 POST。」（新前端 `../api/` 无此问题）；浏览器旧标签页/缓存会保留旧动画——**硬刷新或无痕窗口核对**，DevTools Network 无 three 请求即静态版。

## 2. 开屏双螺旋混合设计（国内线）

- **基层静态帧**：`assets/dna-desktop.webp`（1600×1000，54KB）、`assets/dna-mobile.webp`（780×1688，55KB）+ png 兜底（仅老浏览器）。帧由无头浏览器对**真实 three.js 场景**单帧渲染（reduced-motion、旋转角 0.55）导出，非 AI 生成图；所有设备先秒开静态帧。
- **桌面渐进增强**：视口 >900px 且非 reduced-motion 且 WebGL 可用 → 动态 import 本地 `vendor/` three.js（gzip ≈160KB，**不碰 CDN**）→ 首帧后隐藏静态帧进入慢旋（≈6°/s）；import/WebGL 失败保持静态帧（静态帧即兜底，无降级卡）；视口缩回 ≤900px 停循环换回静态帧。
- **移动/竖屏平板（≤900px）与 reduced-motion**：永远不加载 three.js。实测移动首屏图像 55,274 字节、DOMContentLoaded 60–86ms、零 CDN 请求。
- **设计动机**：国内移动网络对 jsdelivr 经常不通，曾直接报 three.js 超时降级；混合把该故障类在移动侧归零、桌面侧以本地 vendor 消除 CDN 依赖，同时保留桌面旋转观感。
- **与 GitHub 线的差异**：`site/` 与 workers.dev 仍为全断点 CDN 全动画（本节存档时未同步）；后续同步时建议一并换本地 vendor 或静态帧。`vendor/` 在国内线为桌面升级所必需，保留。

## 3. GitHub ↔ Cloudflare 关联配置（海外线）

1. 远端：`origin = git@github.com:hhtttyy/GSGP-BENCH.git`（推送线），`upstream = jmiao24/Paper2Agent`（只同步不推送）。
2. 连线：Cloudflare Dashboard → Workers & Pages → Create → Worker → **Connect to Git** → 授权 GitHub 选 `hhtttyy/GSGP-BENCH`、Production branch `main`；Build command `npm install`（或留空）、Deploy command `npx wrangler deploy`；Save and Deploy。详见 `docs/DEMO-上线清单.md` §3。
3. `wrangler.jsonc` 决定部署目标与路由：`name: gsgp-bench`（**name 决定 Worker，仓库名不决定**）、`main: worker/index.js`、`assets.directory: ./site` + `binding: ASSETS` → `/api/*` 走 Worker、其余静态直出；`vars` 放非密钥配置（`OPENAI_BASE_URL`、`OPENAI_MODEL=qwen3.8-flash`、`AI_DISABLE_THINKING=1`）。
4. 密钥：`OPENAI_API_KEY` 只存 **Worker Secret**（Dashboard → Variables and Secrets 或 `npx wrangler secret put`，使用者执行）；本地开发用 git-ignored `.dev.vars`；生产不设 `AI_MOCK=1`。未配密钥时页面可浏览、AI 按钮显示「AI 服务未配置」，不伪造结果。
5. 自动部署：push `main` → Workers Builds 触发；以 GitHub **check-runs** 与 workers.dev 实际内容验证（「推了但站点没变」多因连线串库或 name 配错）。同账户多 Worker 的 Builds「Git repository」字段各自独立，配置前先核对显示为 `hhtttyy/GSGP-BENCH`；GitHub App 失效时重新授权。
6. 命令行备选（使用者执行）：`npm install && npx wrangler login && npx wrangler deploy`。

## 4. 仓库产物索引

- `deploy-cn/`：国内线源——`www/`（发布前端）、`api/`（server.py、watchdog、api-status、systemd 单元与模板、env.template）、`setup.sh`、`add-site.sh`、`fetch-vendor.sh`、`verify-cn.sh`、`nginx-gsgp.conf`/`nginx-gsgp-snippet.conf`/`nginx-site-template.conf`/`nginx-main.conf`、`architecture.html`（架构图）、`README-部署.md`（逐步 runbook）。
- `deploy-cn.zip`：与 `deploy-cn/` 同内容的发布产物包（随本记录入库，便于无 clone 环境直接取用）。
- 相关文档：`docs/DEMO-上线清单.md`（海外线上线清单）、`site/README.md`（Worker 部署说明）、`docs/证据等级与记录.md`、`docs/MCP认证与展示.md`。

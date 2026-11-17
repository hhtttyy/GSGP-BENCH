# GSGP-BENCH · 部署与运维

> 基因组预测方案智能评估平台。本仓库是 [Paper2Agent](https://github.com/jmiao24/Paper2Agent) 的 fork 实践线（`origin = hhtttyy/GSGP-BENCH`，`upstream = jmiao24/Paper2Agent`，只同步不推送）；上游原文见 [README_Paper2Agent.md](README_Paper2Agent.md)。
> 本文记录两条并行部署线：**GitHub + Cloudflare Workers（海外）** 与 **阿里云 ECS（国内）**。国内线不改动 GitHub/Cloudflare 线的任何配置；本文即国内线的使用流程存档。

## 0. 两条部署线总览

| 线 | 入口 | 开屏双螺旋 | AI 解读/预审 | 更新触发 |
| --- | --- | --- | --- | --- |
| GitHub + Cloudflare Workers | `https://<worker>.<subdomain>.workers.dev`（见 Dashboard） | 全断点 three.js 慢旋（jsdelivr CDN） | Worker `/api/analyze`、`/api/prospective`（Worker Secret 密钥） | push `main` → Workers Builds 自动部署 |
| 阿里云 ECS（国内） | `http://101.200.149.60/gsgp/`（根路径 301 到前缀） | 混合：移动静态帧 / 桌面 three.js 慢旋（本地 vendor） | 回环 `gsgp-api` 127.0.0.1:8787（env 600 密钥），nginx 反代 `/gsgp/api/` | 手动四步更新（见 1.3） |

两线共用同一份前端源 `site/` 与同一套证据账本 `site/data/`；国内线发布产物为 `deploy-cn/`（源）与 `deploy-cn.zip`（产物包）。证据立场不变：演示/探索/复现/跨协议/论文值/流程测试分级陈列，主观估计不混主榜，网站不运行、不托管 MCP。

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
- **与 GitHub 线的差异**：`site/` 与 workers.dev 仍为全断点 CDN 全动画（本记录存档时未同步）；后续同步时建议一并换本地 vendor 或静态帧。`vendor/` 在国内线为桌面升级所必需，保留。

## 3. GitHub ↔ Cloudflare 关联配置（海外线）

1. 远端：`origin = git@github.com:hhtttyy/GSGP-BENCH.git`（推送线），`upstream = jmiao24/Paper2Agent`（只同步不推送）。
2. 连线：Cloudflare Dashboard → Workers & Pages → Create → Worker → **Connect to Git** → 授权 GitHub 选 `hhtttyy/GSGP-BENCH`、Production branch `main`；Build command `npm install`（或留空）、Deploy command `npx wrangler deploy`；Save and Deploy。详见 `docs/DEMO-上线清单.md` §3。
3. `wrangler.jsonc` 决定部署目标与路由：`name: gsgp-bench`（**name 决定 Worker，仓库名不决定**）、`main: worker/index.js`、`assets.directory: ./site` + `binding: ASSETS` → `/api/*` 走 Worker、其余静态直出；`vars` 放非密钥配置（`OPENAI_BASE_URL`、`OPENAI_MODEL=qwen3.8-flash`、`AI_DISABLE_THINKING=1`）。
4. 密钥：`OPENAI_API_KEY` 只存 **Worker Secret**（Dashboard → Variables and Secrets 或 `npx wrangler secret put`，使用者执行）；本地开发用 git-ignored `.dev.vars`；生产不设 `AI_MOCK=1`。未配密钥时页面可浏览、AI 按钮显示「AI 服务未配置」，不伪造结果。
5. 自动部署：push `main` → Workers Builds 触发；以 GitHub **check-runs** 与 workers.dev 实际内容验证（「推了但站点没变」多因连线串库或 name 配错）。同账户多 Worker 的 Builds「Git repository」字段各自独立，配置前先核对显示为 `hhtttyy/GSGP-BENCH`；GitHub App 失效时重新授权。
6. 命令行备选（使用者执行）：`npm install && npx wrangler login && npx wrangler deploy`。
7. **本次入库不影响 Cloudflare**：部署输入（`wrangler.jsonc`、`worker/`、`site/`、`package.json`）零改动；新增的 `deploy-cn/` 与 zip 不在 assets 目录内，Builds 只会原样重部署现有内容。

## 4. 仓库产物索引

- `deploy-cn/`：国内线源——`www/`（发布前端）、`api/`（server.py、watchdog、api-status、systemd 单元与模板、env.template）、`setup.sh`、`add-site.sh`、`fetch-vendor.sh`、`verify-cn.sh`、`nginx-gsgp.conf`/`nginx-gsgp-snippet.conf`/`nginx-site-template.conf`/`nginx-main.conf`、`architecture.html`（架构图）、`README-部署.md`（逐步 runbook）。
- `deploy-cn.zip`：与 `deploy-cn/` 同内容的发布产物包（随本记录入库，便于无 clone 环境直接取用）。
- 相关文档：`docs/DEMO-上线清单.md`（海外线上线清单）、`site/README.md`（Worker 部署说明）、`docs/证据等级与记录.md`、`docs/MCP认证与展示.md`、`README_Paper2Agent.md`（上游原文）。
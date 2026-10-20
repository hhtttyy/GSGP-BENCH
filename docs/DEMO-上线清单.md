# GSGP-Bench Demo 上线清单

> 目标：把 `site/index.html` 通过 Cloudflare Workers（Static Assets + `/api/analyze`）发布为可访问的演示站，并验证 Git 推送后的自动部署。
> 当前阶段不接真实算法运行；页面数值大多为演示值，Worker 只负责静态托管和 AI 文字解读。

## 0. 当前已完成

- 三列交互式演示站（学术期刊风格）：`site/index.html`
- 算法卡片 Paper / Skill / MCP 证据链：论文 DOI 可打开；IFAM Skill 有真实阅读预览；缺项显示“未上传 / 未认证”并支持悬浮、键盘聚焦、触屏点按提示
- IFAM Paper2Skill 包：`agents/ifam/skill/ifam-paper/`（`reviewed_with_limitations`，严格校验通过）
- 公开阅读预览：`site/resources/ifam-paper/`，含 ZIP、SHA-256 清单和限制说明
- 预览已在本地浏览器检查：桌面与 390px 移动端均可读，6 图 3 公式内嵌显示，链接、下载、图片和键盘提示正常，无横向溢出或控制台错误
- IFAM MCP 本地 stdio 原型：`agents/ifam/mcp/`（4 工具、tiny 黄金测试通过、未部署、未认证、未跑真实 IFAM）
- IFAM 上游归档核对：用户已下载 `main.zip`；归档/脚本哈希、demo 表头、注释自动发现规则、`anno_spec` 语义和 `.rand` 列名已记录在 `agents/ifam/mcp/UPSTREAM.md`；执行环境尚未安装
- GBLUP 手动 baseline Skill/MCP：`benchmark/algorithms/gblup/`；站点 Skill 页面与本地 stdio MCP（已认证 MCP 包、不在线托管）
- 第一条真实 GBLUP exploratory 记录：`site/data/results/gblup-sim500.json` + `benchmark/runs/gblup-sim500-mcp-v1/result.json`；经 MCP inspect/fit/export，500×5k 模拟性状，单次 80/20，EXP 非 L1
- IFAM STUB 记录：`site/data/results/ifam-stub-sim500.json` + `benchmark/runs/ifam-stub-sim500-v1/result.json`；fake HIBLUP，仅管线展示
- 介绍页：`site/resources/introduce/index.html`；MCP 认证规则：`docs/MCP认证与展示.md`
- 本地 Paper2Agent 生成套件：`site/resources/generate/`（页面 + 73 文件 ZIP + SHA-256 清单）；网站不执行任何生成
- 提交/认证入口：`site/resources/submit/index.html` + `.github/ISSUE_TEMPLATE/mcp-submission.yml`
- 结果 schema 与证据账本：`benchmark/schema/result.v1.json`、`benchmark/README.md`
- 站点 MIT 归属：`site/LICENSE`
- Worker AI 解读接口：`worker/index.js` + `worker/test.mjs`（16 项测试）；只发送聚合数值，密钥只存 Worker Secret
- Worker 配置：`wrangler.jsonc`（`site/` 静态资源 + `/api/*`）、`package.json`、`.dev.vars.example`
- 本地预览：`node scripts/dev-server.mjs`（默认 `AI_MOCK=1`，无需安装依赖）；或 `npx wrangler dev`
- 规划文档：`docs/GSGP-Bench-规划.md`
- 证据等级规范：`docs/证据等级与记录.md`
- MCP 认证与展示规则：`docs/MCP认证与展示.md`
- GBLUP 端到端示例：`docs/端到端示例-GBLUP.md`
- 研究赋能评估：`docs/MCP与Skill-研究赋能.md`
- Worker 部署说明：`site/README.md`

> 当前大部分评测仍为演示值；GBLUP 是真实探索记录，IFAM 是流程测试。MCP 认证只有已认证/未认证，网站不运行、不托管 MCP；唯一的在线动态能力是把页面聚合数值交给 OpenAI 兼容服务生成解读。

## 1. 在 GitHub 创建你的项目

当前仓库已完成 fork：`origin` 指向 `hhtttyy/GSGP-BENCH`，`upstream` 指向上游 `jmiao24/Paper2Agent`。如果从零开始，先在 GitHub 网页 fork 到你的账号（建议命名为 `GSGP-Bench`），再在本地配置远端：

```bash
# 把原来的 origin 改名为 upstream，保留同步上游的能力
git remote rename origin upstream

# 添加你自己的 fork
git remote add origin git@github.com:<你的账号>/GSGP-Bench.git

# 确认
git remote -v
```

> 不要直接在 `jmiao24/Paper2Agent` 上推送。fork 后，`upstream` 用于同步原项目，`origin` 用于你自己的项目。

## 2. 提交并推送

先把站点里的 GitHub 链接改成你的 fork（保留页脚对上游 Paper2Agent 的 MIT 归属）：

```bash
grep -n "jmiao24/Paper2Agent" site/index.html
# 建议只改导航 GitHub 和页脚 Source；页脚“基于 Paper2Agent”的归属链接保留 upstream
```

再提交：

```bash
git add .gitignore .github agents benchmark docs scripts site worker wrangler.jsonc package.json .dev.vars.example
git commit -m "Add Worker analysis API and comparison note"
git push -u origin main
```

> `docs/*.pdf` 已加入 `.gitignore`，避免把许可不明的论文 PDF 推到公开仓库。
> `.dev.vars`、`node_modules/`、`.wrangler/` 也不应提交；密钥只放本地或 Worker Secret。
> 如果 GitHub 上 fork 的默认分支不是 `main`，先确认分支名再推送。

## 3. 连接 Cloudflare Workers

1. 登录 Cloudflare Dashboard。
2. 进入 **Workers & Pages** → **Create** → **Worker** → **Connect to Git**。
3. 授权 GitHub，选择你的 `GSGP-Bench` 仓库，Production branch 选 `main`。
4. 构建配置（仓库根目录）：
   - Build command: `npm install`（或留空）
   - Deploy command: `npx wrangler deploy`
5. 点击 **Save and Deploy**。
6. 记下 `https://<worker>.<subdomain>.workers.dev`。

> **同一个 Cloudflare 账户下多个 Worker 容易串库**：Worker 的 Settings → Builds → “Git repository” 是各自独立的字段，改一个不会影响另一个，但配置时容易把仓库选错。
> 先在面板上确认 GSGP-BENCH 的 “Git repository” 显示 `hhtttyy/GSGP-BENCH`，再点 Save and Deploy。
> 如果页面顶部出现 “This project is disconnected from your Git account” 或 “Error fetching GitHub User or Organization details”，说明 GitHub App 安装已失效：断开连线后重新连接，必要时到 GitHub → Settings → Applications → Installed GitHub Apps 里重新授权 Cloudflare（私有仓库还要勾选该私有仓库）。
> `wrangler.jsonc` 里的 `name` 决定部署到哪个 Worker（`gsgp-bench`），仓库名不决定；配错连线时，Cloudflare 会按配置里的 `name` 部署，容易出现“推了但站点没变”的错觉。

`wrangler.jsonc` 已声明：

```jsonc
{
  "main": "worker/index.js",
  "assets": { "directory": "./site", "binding": "ASSETS" }
}
```

因此 `/api/*` 由 Worker 处理，其余路径直接返回 `site/` 中的静态文件。不需要 Pages 的 build output 配置。

### 也可以用命令行部署

```bash
npm install
npx wrangler login
npx wrangler deploy
```

首次部署后在 Dashboard → Worker → **Settings** → **Variables and Secrets**：

- `OPENAI_API_KEY`：Secret，必须；
- `OPENAI_BASE_URL`：已在 `wrangler.jsonc` 设为 `https://maas.qianwenaiapi.com/compatible-mode/v1`；
- `OPENAI_MODEL`：已设为 `qwen3.8-flash`；
- `AI_DISABLE_THINKING`：已设为 `1`，用于关闭 Qwen 的推理 token，缩短等待时间；换普通模型时删除。

或：

```bash
npx wrangler secret put OPENAI_API_KEY
npx wrangler secret put OPENAI_BASE_URL   # 可选
```

> 生产环境不要设置 `AI_MOCK=1`；它只用于本地预览。
> 若暂时不配置密钥，页面仍可正常浏览，点击“生成 AI 解读”会显示“AI 服务未配置”，不会伪造结果。

## 4. 验证自动部署

1. 打开生产地址，确认三列布局、筛选、指标切换、详情抽屉都正常。
2. 确认算法卡只展示已提供论文 Skill 的方法（GBLUP、IFAM）；论文链接能打开 DOI，IFAM 论文 Skill 显示“预览”，MCP 工具显示“已认证/未认证”；悬浮、键盘聚焦和触屏点按都能看到说明。
3. 确认 GBLUP × GSGP-Sim 500×5k 显示 **探索**（真实单次划分），IFAM × 同一数据集显示 **流程测试**；打开详情能看到 run ID、划分、实现和证据账本路径。
4. 打开“生成”，确认本地套件可下载、清单 SHA-256 一致；打开“介绍”，确认面向用户、能力、认证规则、证据等级和 GBLUP/IFAM 例子都清楚。
5. 滚动到结果表下方，点击 **生成 AI 解读**：
   - 配置密钥后返回真实模型文本，并显示模型名；
   - 未配置密钥时返回明确错误，不产生假结果；
   - 切换指标或选择后，旧解读清空并要求重新生成；
   - 输出始终带“AI 辅助 · 非证据”和“AI 生成 · 仅供参考”。
6. 在浏览器开发者工具确认 `/api/analyze` 请求体只含方法名、数据集名、指标、状态和聚合数值，不含样本 ID、基因型、表型或划分文件。
7. 确认页脚显示 Paper2Agent / MIT 归属，`/LICENSE` 可访问。
8. 在 390px 左右宽度检查：三列已纵向重排、页面无横向滚动、结果表可横向滑动、图表可左右滑动、AI 解读面板不溢出。
9. 打开“介绍 / 生成 / 提交”页面，确认桌面和移动端都可读。
10. 随便改一个页面文案（例如页脚版本号），push 到 `main`，确认 Cloudflare 自动触发新部署。
11. 新建一个分支并提 PR，确认生成 Preview Deployment。

### 4.1 备用通道：GitHub Actions 部署（可选，当前未启用）

Workers Builds 的连线曾出现过"Git repository 指错仓库"和"构建环境初始化超时"两类故障。若再次发生且短时间内修不好，可以用一条 Actions 通道兜底：`main` 一有推送就自己跑 `npx wrangler deploy`，不依赖面板连线。

> 截至 2026-10-21，这条通道的工作流文件**没有入库**（两个 Worker 的原生连线都已验证可用，不再保留冗余配置）。需要时按下述步骤临时加回 `.github/workflows/deploy.yml` 即可，内容是：checkout → setup-node 22 → `npm install` → `npx wrangler deploy`（GSGP-BENCH 在仓库根，reading-coach 需把工作目录设为 `coach-deploy`）。

启用前需要两步（都在浏览器里完成）：

1. Cloudflare → My Profile → API Tokens → Create Token，权限选 **Edit Cloudflare Workers**（含 Workers Scripts:Edit），得到 `CLOUDFLARE_API_TOKEN`；同页可查到 `CLOUDFLARE_ACCOUNT_ID`。
2. GitHub → GSGP-BENCH → Settings → Secrets and variables → Actions → New repository secret，加入上面两个值。

之后 push 到 `main`，在仓库的 Actions 标签里能看到部署结果。两条通道并存时建议只留一条，避免同一次推送被部署两遍。

## 5. 可选：绑定自定义域名

- Worker → **Settings** → **Domains & Routes** → **Add custom domain**。
- 按提示在 Cloudflare DNS 添加记录，TLS 会自动签发。
- 上线前实测中国大陆网络访问；`workers.dev` 在部分网络环境可能不稳定。
- 公开上线前设置 AI 服务商侧的预算和速率上限；若流量不可控，可先隐藏该按钮或按套餐启用 Cloudflare Rate Limiting。

## 6. 下一步：把演示值换成真实结果

按以下顺序推进，避免一次性引入太多变量：

1. 定稿结果 JSON schema（参考规划文档第 6.3 节）。
2. 用 GBLUP 在一个 tiny fixture 上跑出真实预测，生成第一个结果 JSON。
3. 把 `site/index.html` 的内联演示数据替换为 `site/data/results/*.json`。
4. 继续 IFAM 垂直切片：Paper Skill 已完成；用户已下载上游归档，脚本、demo 表头、注释发现规则和输出列名已校准；MCP 四工具 stdio 原型和独立 runner 已实现。下一步由用户安装 R/HIBLUP 并运行最小执行验收。
5. IFAM 打通后，再做 SBayesRC 的公开数据 L2 探索。
6. 最后加 GitHub 论文提交表单、自动检查和人工审核流程。

> 大文件下载前先确认磁盘、带宽和数据许可；受限数据（UKB/WTCCC/Yorkshire 等）只允许在受控环境使用，不上传公开仓库或站点。
> 当前所有下载由用户执行，助手不自动抓取；IFAM 归档已由用户下载并核对，哈希见 `agents/ifam/mcp/UPSTREAM.md`。

## 不要做的事

- 不要在 Cloudflare Worker 里执行 R/GCTB 或不可信论文代码。
- 不要把 UKB/WTCCC 等受限数据提交到公开仓库，也不要发给 AI 服务。
- 不要把 API key 写进前端、`wrangler.jsonc` 或 Git；只放 Worker Secret。
- 不要把演示值包装成实测结论；页面上必须保留“演示数据”提示。
- 不要把 AI 解读当作证据、排名或论文结论；它只能解释页面已有数值。
- 不要把未认证工具宣传为已认证或在线服务。
- 不要在没有统一划分和指标的情况下做跨论文排名。

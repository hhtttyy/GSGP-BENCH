# GSGP-Bench Demo Site

这是一个由 **Cloudflare Worker + Static Assets** 托管的演示站：页面本身是静态 HTML，另有一个同源接口 `/api/analyze` 用于生成“AI 解读”。

- 左列：GSGP 算法多选；只展示已提供论文 Skill 的方法，每张算法卡附 **论文 / 论文 Skill / MCP 工具** 资源状态
- 中列：常用数据集多选
- 右列：同条件下的指标对比、结果矩阵、运行记录抽屉和 AI 解读
- 介绍页、本地生成和提交认证：面向用户、能力边界、证据等级和已跑通的例子

> 重要：除标记为 **探索** 的 GBLUP 单元和 **流程测试** 的 IFAM 单元外，页面评测数值均为**演示值**，不是真实运行结果。网站不运行任何预测算法，也不执行 MCP；Worker 只把页面上的聚合数值发给 OpenAI 兼容服务生成文字解读。正式版本必须由 benchmark runner 产出的结果 JSON 驱动。

## 设计说明

当前版本采用“学术期刊证据板”的视觉语言：

- 衬线标题 + 无衬线正文 + 等宽数据注记；
- 冷灰纸面、深墨文字、苔绿主色、赤陶色论文值；
- A / B / C 三栏、Figure 1 / Table 1 的图表规范；
- 复现值（实心柱）与论文报告值（斜线柱）在视觉上严格区分；
- 页脚保留 Paper2Agent 的 MIT 归属，`site/LICENSE` 随站点一起部署。

## 算法卡片的资源状态

每张算法卡的下沿是一条可追溯的证据链：

- **Paper ↗**：跳转到 DOI（当前展示 GBLUP 2008、IFAM 2026）。
- **论文 Skill**：IFAM 已有真实的 Paper2Skill 预览（`reviewed_with_limitations`），标为“预览”并可打开；GBLUP 提供自建基线 Skill。
- **MCP 工具**：GBLUP 包已认证；IFAM 未认证（本地 stdio 原型 + fake HIBLUP STUB，等待真实执行）。没有在线托管的 MCP。
- **GBLUP baseline**：站点提供自建 baseline Skill 页面（`resources/gblup-baseline/index.html`）；本地 stdio MCP 包已通过中央测试，显示 **已认证**；不在线托管，结果仍为 EXP。
- **GBLUP 真实 exploratory 记录**：`data/results/gblup-sim500.json`，由 GBLUP MCP → 独立 runner 产生；500×5k 上游 demo 基因型上的模拟性状，单次 80/20，Pearson r 0.508，明确标记 EXP，不是 L1。
- **IFAM STUB 记录**：`data/results/ifam-stub-sim500.json`，真实 IFAM.R 编排 + fake HIBLUP；只展示 Paper2Agent/MCP 管线，STUB 数值不可引用。
- **介绍页**：`resources/introduce/index.html`，说明面向用户、三项核心能力、认证规则、证据等级和 GBLUP/IFAM 两个已跑通例子。

缺项支持鼠标悬浮、键盘聚焦与触屏点按提示，并会说明“为什么未上传/未认证”。只有当资源真实存在并通过审核后，渲染逻辑才会把它变成可访问链接；当前没有任何在线托管的 MCP；GBLUP 的 MCP 包已认证，但由用户自行运行。

## IFAM Paper Skill 预览

`site/resources/ifam-paper/` 是 **公开阅读预览**，不是 MCP 服务，也不是基准结果：

- 源文件在 `agents/ifam/skill/ifam-paper/`，状态 `reviewed_with_limitations`；
- 预览包含论文全文、阅读导航、6 张图与 3 个公式，不含数据、代码或补充材料；
- 页面显式列出审校记录、缺失限制、CC BY 4.0 归属和“不声称什么”；
- 下载包 `ifam-paper-skill.zip` 和 `skill-manifest.json` 由脚本生成。

## 本地 Paper2Agent 生成套件

`site/resources/generate/` 提供完全本地的生成入口：

- `index.html`：五步生成说明、可复制提示词、下载和提交入口；
- `paper2agent-local-kit.zip`：Paper2Agent skills、README、PROMPT、MIT License 和 MCP submission 模板，73 个文件；
- `kit-manifest.json`：文件、大小、SHA-256 清单；
- 网站不执行论文代码、不上传论文/数据、不托管 MCP。

生成后通过 `resources/submit/index.html` 和 GitHub Issue 模板提交中央认证。

## 真实 GBLUP 证据

`site/data/results/gblup-sim500.json` 是前端消费的第一条真实结果记录：

- 数据：`local_data/ifam-demo-500x5k`（上游 demo 基因型子集，未提交）；
- 性状：模拟性状，h² = 0.5，seed `20261019`；
- 模型：GBLUP / VanRaden GRM / 单随机效应 REML，通过本地 stdio baseline MCP 执行；
- 划分：一次 80/20，400 训练 / 100 验证；
- 指标：Pearson r 0.508，R² 0.258，bias 1.212；
- 证据：`exploratory`，单次划分，未认证；
- MCP：manual baseline，不是 Paper2Agent 自动生成，也不能在静态网页内执行；认证记录在 `benchmark/algorithms/gblup/certification.json`。

页面会把它显示为 **探索**（点状），与 **演示** 和 **流程测试** 区分。结果记录由
`benchmark/run_gblup_sim.py` 生成，schema 在 `benchmark/schema/result.v1.json`；
证据账本与复现说明在 `benchmark/README.md`；baseline Skill 文档在
`benchmark/algorithms/gblup/SKILL.md`。原始数据与个体预测只保存在
`local_data/`，不部署、不提交。

重新生成：

```bash
python3 scripts/build_ifam_skill_preview.py
```

修改论文包时应改 `agents/ifam/skill/ifam-paper/`，再运行脚本；不要直接编辑站点副本。MCP 契约与合成夹具仍在 `agents/ifam/mcp/`，**没有**被放进公开站点。

![算法资源状态](../docs/prototype/gsgp-bench-v1-resources.png)

产品与研究路线见：

- [`docs/GSGP-Bench-规划.md`](../docs/GSGP-Bench-规划.md)
- [`docs/MCP与Skill-研究赋能.md`](../docs/MCP与Skill-研究赋能.md)
- [`docs/DEMO-上线清单.md`](../docs/DEMO-上线清单.md)
- [`docs/证据等级与记录.md`](../docs/证据等级与记录.md)
- [`docs/MCP认证与展示.md`](../docs/MCP认证与展示.md)
- [`docs/端到端示例-GBLUP.md`](../docs/端到端示例-GBLUP.md)
- [介绍页](resources/introduce/index.html)
- [本地生成套件](resources/generate/index.html)
- [提交 MCP](resources/submit/index.html)
- [GitHub MCP submission 模板](../.github/ISSUE_TEMPLATE/mcp-submission.yml)

## AI 解读（OpenAI 兼容 API）

右列结果表下方的 **AI 解读** 是唯一的在线动态能力：

- 点击“生成 AI 解读”后，浏览器把当前视图的方法名、数据集名、指标、证据状态和聚合数值 `POST /api/analyze`；
- Worker 使用 `OPENAI_API_KEY` 调用任意 OpenAI 兼容的 `/chat/completions` 服务，返回一段中文观察；
- 不发送原始基因型、表型、样本 ID、划分文件或 held-out truth；不运行预测模型；
- 输出固定标注“AI 辅助 · 非证据”，不能替代结果表、运行记录或人工审核；
- 密钥只存在 Worker Secret 中，永不下发到浏览器，也不写进仓库。

接口的防护：仅接受 `POST`、同源浏览器请求；请求体上限 24 KB、最多 24 个单元格；60 秒超时；`max_tokens` 700；上游错误只返回脱敏信息。

### 本地开发

不安装任何依赖即可预览完整的 Worker 行为（默认使用带标注的本地 Mock，不调用外部 API）：

```bash
node scripts/dev-server.mjs
# http://127.0.0.1:4173
```

也可以使用 Wrangler：

```bash
npm install
cp .dev.vars.example .dev.vars   # 本地文件，已被 .gitignore 忽略
npx wrangler dev                 # 读取 .dev.vars，默认 AI_MOCK=1
```

`.dev.vars` 示例：

```dotenv
AI_MOCK=1
# OPENAI_API_KEY=sk-...
# OPENAI_BASE_URL=https://api.openai.com/v1
# OPENAI_MODEL=gpt-4o-mini
# AI_DISABLE_THINKING=1   # Qwen 等混合推理模型可开启，减少等待
```

把 `AI_MOCK` 改为 `0` 并填入真实密钥后，本地才会调用兼容服务。
当前 `wrangler.jsonc` 的默认服务是通义千问 MaaS：`https://maas.qianwenaiapi.com/compatible-mode/v1` + `qwen3.8-flash`，并开启 `AI_DISABLE_THINKING=1`；更换服务时同步修改这三项。

### 部署到 Cloudflare Workers

1. 在 Cloudflare Dashboard → **Workers & Pages** → **Create** → **Worker**，连接 GitHub 仓库 `hhtttyy/GSGP-BENCH`。
2. 构建配置：
   - Root directory: 仓库根目录
   - Build command: 留空或 `npm install`
   - Deploy command: `npx wrangler deploy`
3. `wrangler.jsonc` 已完成静态资源绑定：`assets.directory = "./site"`、`assets.binding = "ASSETS"`；`/api/*` 进入 Worker，其余路径由静态资源返回。
4. 在 Worker → **Settings** → **Variables and Secrets** 添加：
   - `OPENAI_API_KEY`（Secret，必须）
   - `OPENAI_BASE_URL`（Variable，已在 `wrangler.jsonc` 中设为通义千问 MaaS 地址）
   - `OPENAI_MODEL`（Variable，已设为 `qwen3.8-flash`）
   - `AI_DISABLE_THINKING`（Variable，已设为 `1`；换用普通模型时删除）
5. 部署后打开 `https://<worker>.<subdomain>.workers.dev`，确认页面、结果 JSON 和 `/api/analyze` 都正常。

使用命令行部署时：

```bash
npx wrangler login
npx wrangler secret put OPENAI_API_KEY
npx wrangler secret put OPENAI_BASE_URL   # 可选，自定义兼容服务
npx wrangler deploy
```

> 不要把 `.dev.vars`、密钥或真实数据提交到 Git。生产环境不要设置 `AI_MOCK=1`。
> 每次 AI 生成都会消耗服务商额度：请在 AI 服务商侧设置预算与速率上限；Cloudflare 免费套餐每天 10 万次请求，但真正的成本在模型调用。若公开站点流量不可控，可先不上线该按钮，或按套餐启用 Rate Limiting。

### 自定义域名

Worker → **Settings** → **Domains & Routes** → **Add custom domain**。按提示在 Cloudflare DNS 添加记录，TLS 自动签发。上线前实测目标网络环境。

## 数据替换路径

当前演示数据内联在 `index.html` 的 `<script>` 中。正式版本建议：

```text
site/
├── index.html
├── LICENSE
├── resources/
│   └── ifam-paper/          # 已生成的阅读预览（非结果数据）
└── data/
    ├── algorithms.json
    ├── datasets.json
    └── results/
        ├── gblup__sim1000g__height.json
        └── ...
```

构建时或运行时加载 JSON，页面只负责展示。每个结果文件遵循 `benchmark/schema/result.schema.json`，并包含 run ID、代码 commit、环境、划分、指标和产物路径。

## 介绍页与本地生成

- 介绍页说明面向谁、提供什么、认证怎么看、结果等级怎么用，并用 GBLUP/IFAM 两个已跑通例子讲解边界。
- 本地生成页提供 Paper2Agent 套件、提示词和提交入口；网站不执行生成、不上传论文/数据。
- 提交页只负责 GitHub Issue 入口和认证规则说明；不托管 MCP。
- 所有演示值不能引用；探索和流程测试仍分别标注。

## 注意

- 不要在 Cloudflare Worker 里执行 R/GCTB 或论文代码；Worker 只做静态托管和 AI 文字解读。
- 不要把 UKB/WTCCC 等受限数据上传到公开仓库，也不要发给 AI 服务。
- AI 解读只基于页面聚合数值，必须保留“AI 辅助 · 非证据”标注。
- 演示值与实测值必须在视觉上明确区分。
- 修改页面后，至少检查 1280px 桌面和 390px 移动端，确认无横向溢出、控制台无报错。

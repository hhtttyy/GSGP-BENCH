# GSGP-Bench Demo Site

这是一个**纯静态演示站**，用于确认 GSGP-Bench 的产品形态：

- 左列：GSGP 算法多选（最多 4 个）；每张算法卡附 **论文 / 阅读包 / 工具** 资源状态
- 中列：常用数据集多选（最多 3 个）
- 右列：同条件下的指标对比、结果矩阵与运行记录抽屉
- 方法档案与本地生成：方法说明、提交认证和 Paper2Agent 套件

> 重要：除标记为 **探索** 的 GBLUP 单元和 **流程测试** 的 IFAM 单元外，页面评测数值均为**演示值**，不是真实运行结果。网站不运行任何 MCP。正式版本必须由 benchmark runner 产出的结果 JSON 驱动。

## 设计说明

当前版本采用“学术期刊证据板”的视觉语言：

- 衬线标题 + 无衬线正文 + 等宽数据注记；
- 冷灰纸面、深墨文字、苔绿主色、赤陶色论文值；
- A / B / C 三栏、Figure 1 / Table 1 的图表规范；
- 复现值（实心柱）与论文报告值（斜线柱）在视觉上严格区分；
- 页脚保留 Paper2Agent 的 MIT 归属，`site/LICENSE` 随站点一起部署。

## 算法卡片的资源状态

每张算法卡的下沿是一条可追溯的证据链：

- **Paper ↗**：跳转到 DOI（VanRaden 2008、Meuwissen 2001、IFAM 2026、SBayesRC 2024、BayesR 2012、XGBoost 2016）。
- **Skill**：IFAM 已有真实的阅读包预览（`reviewed_with_limitations`），标为“预览”并可打开；其他算法仍显示“未上传”。
- **MCP 状态**：GBLUP 包已认证；IFAM 未认证（本地 stdio 原型 + fake HIBLUP STUB，等待真实执行）；SBayesRC 第二批。没有在线托管的 MCP。
- **GBLUP baseline**：站点提供自建 baseline Skill 页面（`resources/gblup-baseline/index.html`）；本地 stdio MCP 包已通过中央测试，显示 **已认证**；不在线托管，结果仍为 EXP。
- **GBLUP 真实 exploratory 记录**：`data/results/gblup-sim500.json`，由 GBLUP MCP → 独立 runner 产生；500×5k 上游 demo 基因型上的模拟性状，单次 80/20，Pearson r 0.508，明确标记 EXP，不是 L1。
- **IFAM STUB 记录**：`data/results/ifam-stub-sim500.json`，真实 IFAM.R 编排 + fake HIBLUP；只展示 Paper2Agent/MCP 管线，STUB 数值不可引用。
- **方法档案页**：`resources/methods/index.html`，集中列出 GBLUP/IFAM 的论文、Skill、MCP、验证和证据状态。

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
- [方法档案页](resources/methods/index.html)
- [本地生成套件](resources/generate/index.html)
- [提交 MCP](resources/submit/index.html)
- [GitHub MCP submission 模板](../.github/ISSUE_TEMPLATE/mcp-submission.yml)

## 本地预览

在仓库根目录运行：

```bash
python3 -m http.server 8000 --directory site
```

打开 <http://localhost:8000>。页面不依赖构建工具或外部 CDN。

## 部署到 Cloudflare Pages（Git 自动部署）

1. 先把仓库 fork 到你的 GitHub 账号，并把 `site/` 推送到 `main`。
2. Cloudflare Dashboard → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**。
3. 选择你的仓库，配置：
   - Production branch: `main`
   - Root directory: `site`
   - Build command: 留空；如果界面要求必填，填 `exit 0`
   - Build output directory: `.`
4. 保存并部署，得到 `https://<project>.pages.dev`。
5. 之后每次 push 到 `main` 自动部署；PR 会自动生成预览地址。

如果当前 Cloudflare 界面不接受空 build command，也可以：

- Root directory 留空
- Build command: `exit 0`
- Build output directory: `site`

两种配置等价，以控制台实际校验为准。

### 只想最快看到效果

Cloudflare Pages 支持直接上传静态文件（Direct Upload）：把 `site/` 目录拖进去即可。但这种方式**没有 Git 自动部署**，只适合临时演示。

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

## 方法档案与本地生成

- 方法档案页集中列出 GBLUP/IFAM 的论文、阅读包、运行工具、验证和证据状态。
- 本地生成页提供 Paper2Agent 套件、提示词和提交入口；网站不执行生成、不上传论文/数据。
- 提交页只负责 GitHub Issue 入口和认证规则说明；不托管 MCP。
- 所有演示值不能引用；探索和流程测试仍分别标注。

## 注意

- 不要在 Cloudflare Worker 里执行 R/GCTB 或论文代码。
- 不要把 UKB/WTCCC 等受限数据上传到公开仓库。
- 演示值与实测值必须在视觉上明确区分。
- 修改页面后，至少检查 1280px 桌面和 390px 移动端，确认无横向溢出、控制台无报错。

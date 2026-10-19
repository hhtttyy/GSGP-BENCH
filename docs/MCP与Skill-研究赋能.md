# 从静态榜单到研究基础设施：MCP、Skill 与 GSGP 论文复现评估

> 版本：v1 · 2026-10-18  
> 性质：产品与技术评估，不是已完成的复现实验报告。  
> 关联：[GSGP-Bench 规划](GSGP-Bench-规划.md) · [Paper2Agent 论文](https://www.nature.com/articles/s41586-026-11044-y) · [Paper2Agent 仓库](https://github.com/jmiao24/Paper2Agent)

## 0. 结论先行

**Paper2Agent 论文真正有价值的点，不是“让大模型替你写代码”，而是把论文变成一个经过验证、可被 Agent 调用、能追溯到原始代码的 MCP 服务。** 它的核心资产是“可靠绑定 + 独立验证 + 可追溯”，而不是生成出来的那层包装代码。

对 GSGP-Bench 来说，这意味着产品不应停在静态榜单。更合适的定位是：

> **一个面向基因组预测的研究基础设施：让论文可读、方法可跑、结果可比、贡献可认证。**

它由三层组成，三者缺一不可：

| 层 | 回答的问题 | 载体 | 在本项目中的角色 |
| --- | --- | --- | --- |
| **Paper Skill** | “这篇论文在说什么？适不适合我？结论有什么前提？” | 经过逐页审校的论文知识包 | 研究顾问、选型、解释、引用 |
| **Paper MCP** | “能不能在我的数据上跑？怎么跑？” | 绑定官方代码、经独立验证的 MCP 工具 | 执行层、私有数据本地运行 |
| **Benchmark / Evidence** | “它和别的方法比，数字可信吗？” | 固定数据与划分、独立评测、运行档案 | 公信力、认证、排行榜 |

三个常见误解需要先排除：

1. **MCP 不是另一个排行榜。** MCP 是“让 Agent 能调用方法”的接口，本身不负责公平比较。把评测逻辑塞进作者的包装代码，正是 Paper2MCP 明确禁止的事情。
2. **Skill 不是可执行程序。** 它是 Agent 的操作手册和知识库，负责“读得懂、问得清、说得有依据”，不负责跑模型。
3. **能跑通不等于论文结论成立。** Paper2Agent 的准确率衡量的是“忠实执行教程/方法”的能力，不是“新数据上科学结论正确”的保证。

关于两篇测试论文的结论：

- **IFAM 适合作为第一个真实试点。** 官方代码 MIT、数据接口清楚，Duroc 数据公开，方法级复现（在我们的开放数据和协议上跑通并比较）可行。但 UKB、WTCCC、Yorkshire 的原始数据不可公开获取或有禁运，**论文全部表格的精确复现现在做不到**。
- **SBayesRC 适合第二阶段。** 代码、LD/注释资源和 Docker 镜像较完整，但在公开数据上只能做“汇总统计 + 公开 LD + 模拟/公开汇总”的 **L2 级**探索；论文中依赖 UKB、UK10K、LifeLines 的精确表格与跨祖先结论，需要受限数据，暂不作为公开主榜目标。

---

## 1. Paper2Agent 论文的重点

### 1.1 它解决的不是“读论文”，而是“用论文”

传统论文的使用链路是：发现论文 → 读正文 → 找代码仓库 → 配环境 → 理解输入输出 → 改代码 → 才能用于新数据。任何一步失败，方法就无法真正被复用。

Paper2Agent 把这个链路压缩成一个 Agent 可调用的服务：

```text
论文 + 补充材料 + 代码仓库
        │
        ▼
   Paper2MCP：提取、绑定、验证、打包
        │
        ▼
   远程 MCP server（工具 / 资源 / 提示词）
        │
        ▼
  任意 MCP 客户端（Claude Code、IDE、聊天 Agent…）
        │
        ▼
  “把这个方法用在我的数据上”
```

论文中的两个组成部分：

- **Paper2MCP**：从论文和代码库构建远程 MCP server。
- **Agent layer**：把 MCP server 作为上下文提供给一个通用 Agent，形成这篇论文的“论文代理”。

每个 MCP server 包含三类东西：

| 组件 | 含义 | 例子（GSGP 语境） |
| --- | --- | --- |
| **Tools** | 可执行函数，绑定论文官方实现 | `ifam_fit()`、`sbrc_run()` |
| **Resources** | 静态资产：原文、补充材料、数据说明、代码链接 | IFAM 的论文包、Duroc 数据字典、示例输入 |
| **Prompts** | 多步工作流模板，告诉 Agent 正确顺序 | “先校验 PLINK 输入，再准备注释，再拟合，最后导出预测” |

这三者结合，才让 Agent 不只会“解释论文”，还能按论文的流程做事。

### 1.2 构建流程与质量闸门

仓库中的 Paper2MCP 把转换拆成 6 个阶段，每个阶段有明确的完成标记：

| 阶段 | 做什么 | 关键要求 |
| --- | --- | --- |
| 1. 环境与工具选择 | 找到可独立完成的任务，而不是照抄教程标题 | 工具必须对“新输入”有用；合并重复步骤 |
| 2. 源执行与参考结果 | 先跑通官方代码，保存输入、输出、图和元数据 | 参考结果必须来自上游代码，不是重写实现 |
| 3. 实现与独立验证 | 写最小包装；由**未参与实现**的验证者复核 | 新验证者、独立运行、检查参考一致性 |
| 4. MCP 集成 | 把工具、资源、提示词封装成 server | 工具 schema 明确，输入输出可序列化 |
| 5. 运行时验证 | 在**全新位置**安装、启动、调用 | 通过 stdio 启动、工具清单、验收调用 |
| 6. 文档与交付 | ZIP、USAGE、限制说明 | 解压后在新环境真实调用通过 |

其中三条对 GSGP-Bench 特别重要：

1. **每个工具必须绑定仓库中真实存在的代码。** 仓库没有实现的方法，不允许包装者“补写一个算法”。
2. **生产包装不负责重算 benchmark 指标。** 评测属于独立 harness；否则作者很容易在包装层无意或有意地改变指标定义。
3. **验证者必须独立于实现者。** 这不是流程洁癖，而是防止“实现者的理解错误”被同一批人验证通过。

### 1.3 论文给出的证据

以下是论文报告的结果，**不是本项目的实验结果**：

| 评估 | 结果 |
| --- | --- |
| 100 篇计算生物学论文 | 74 篇成功 agentify，产出 599 个候选工具，593 个通过自动验证 |
| 300 道教程型问题 | Paper2Agent 91.2 ± 1.6%；Claude Code + 仓库 80.3 ± 2.3%；Sonnet 4.6 + 仓库 86.3 ± 1.1% |
| 单次查询成本/延迟 | US$0.20 / 1.6 分钟；直接使用 Sonnet 4 + 论文/仓库为 US$0.38 / 4.3 分钟 |
| 26 篇数据/发现型论文（无工具层） | 资源层 89.0 ± 3.1%，浏览器基线 82.0 ± 3.8%；约 34 倍便宜、15 倍快 |
| 10 篇非生物领域计算论文 | 42 个执行任务，98.1 ± 0.8% |
| AlphaGenome 案例 | 22 个工具，约 45 分钟，US$14 |
| Scanpy 案例 | 7 个工具，约 45 分钟，US$13 |

这些数字说明两件事：**单篇论文的转换成本已经很低；但转换成功率、长期可维护性和科学判断仍然是瓶颈。**

### 1.4 论文没有解决什么

必须把边界说清楚，否则产品会过度承诺：

- **26% 的论文无法成功转换。** 主要原因是缺少可执行代码、缺少数据/模型产物、环境或依赖不可恢复、脚本无法泛化。这不是提示词问题，不能靠“更聪明的 Agent”完全消除。
- **教程题准确率不等于新数据上的科学正确性。** 论文自己也强调，开放式科学推理和机制解释仍然需要 human-in-the-loop。
- **没有领域评测协议。** Paper2Agent 不定义“什么叫同数据、同划分、同指标”，也不提供排行榜或认证体系。这正是 GSGP-Bench 要补的。
- **不保证托管服务的长期可用性。** 远程 MCP 仍然需要算力、依赖维护、版本管理和安全边界。论文演示了部署路径，不等于交付了运维方案。
- **不解决数据许可与受限数据。** 代码能打包，不代表数据能公开；这在 GSGP 中比在纯软件论文中更严重。

论文里有一句话值得直接借用为产品原则：**论文能否被顺利 agentify，本身可以作为可复现性的一个实用信号。** 我们的版本可以更进一步：把“能否被认证为可运行、可比较的研究对象”变成 GSGP 领域的信誉信号。

### 1.5 仓库比论文多了什么：Paper2Skill

Paper2Agent 的仓库额外提供了 **Paper2Skill** 工作流。它不是论文的核心实验，但对本项目非常关键。

它把论文 PDF、补充材料、表格和图，转换成一个可被 Agent 阅读的 `<paper>-paper` 知识包：

```text
<identifier>-paper/
├── SKILL.md                  # 导航、阅读顺序、使用边界
├── references/
│   ├── index.md
│   ├── paper.md              # 正文结构化文本
│   └── supplement.md         # 补充材料
└── assets/
    ├── figure/
    ├── supp_figs/
    ├── table/
    └── supp_table/
```

它的价值不在于“把 PDF 转成 Markdown”，而在于：

- 逐页审校，保留正文、补充材料、图表和表格之间的对应关系；
- 保留图注和表注的可检索文本，避免 Agent 只读到正文而漏掉关键限制；
- 用严格状态标记质量：`reviewed`、`reviewed_with_limitations`、`unreviewed`、`unresolved_discrepancies`、`mechanical_failure`；
- 把审校证据放在交付物之外，交付包只包含经过确认的内容。

对 GSGP 尤其重要：很多方法的关键假设不在正文，而在补充表、图注、数据预处理段落里。比如“是否使用了 trait-specific GWAS 注释”“划分是在特征筛选之前还是之后”“AUC 是在哪个验证集上算的”。这些细节决定了结果能不能比较。

> **结论：** 论文提供的是“构建可执行 MCP”的方法；仓库提供的 Paper2Skill 是“构建可信知识包”的方法。GSGP-Bench 需要两者，再加一层领域评测协议。

---

## 2. Skill、MCP、Benchmark：三者到底怎么配合

### 2.1 一张表看清区别

| 维度 | Paper Skill | Paper MCP | Benchmark / Evidence |
| --- | --- | --- | --- |
| 本质 | 结构化知识 + 操作手册 | 标准化工具服务 | 评测协议 + 运行档案 |
| 是否执行代码 | 否 | 是 | 是（独立 harness） |
| 谁消费 | 研究 Agent、人 | Agent、脚本、本地客户端 | 评审、网站、作者、用户 |
| 关键保证 | 内容经过审校、可引用 | 工具绑定真实代码、可重复调用 | 同数据/同划分/同指标、可追溯 |
| 典型失败 | 断章取义、漏掉补充材料限制 | 环境漂移、输入不合法、超时 | 数据泄漏、划分不一致、指标被改写 |
| 类比 | 实验室的操作规程与文献笔记 | 一台带标准接口的仪器 | 多家实验室的环形比对与校准 |
| GSGP 例子 | “IFAM 适不适合只有基因位置的注释？” | `ifam_fit(plink, pheno, annotations)` | “在 Duroc 的同一划分上，IFAM 相对 GBLUP 的 Pearson r 差值” |

### 2.2 一个具体问题如何走完三层

假设一个育种研究者问：

> “我有 2,000 头 Duroc 猪、50K SNP、背膘厚表型，只有基因位置注释，想做基因组预测。IFAM 会比 GBLUP 更好吗？我该怎么设计实验？”

**第一层：Skill 回答“是否值得、有什么前提、怎么设计”**

Agent 从 IFAM 的论文知识包中检索并回答：

- IFAM 的核心是把不同功能注释对应的 SNP 组作为多个随机效应，并自动合并贡献相近的组；
- 论文报告 Duroc 上相对 GBLUP 平均提升 4.59%，但这是论文数据、论文注释和论文划分下的结果；
- 论文同时指出，去掉 trait-specific GWAS 注释后，UKB 上的增益从 6.15% 降到 1.40%，牲畜/作物上的功能注释单独增益也有限；
- 因此，“只有基因位置注释”与论文的最佳设置并不相同，不能直接承诺提升；
- 建议先做 GBLUP 基线，再用训练折内部生成 trait-specific 显著 SNP 列表，比较 IFAM 与 GBLUP；划分必须先于任何特征筛选，避免泄漏；
- 给出样本量、重复次数、评价指标和预期不确定性。

这一层输出的是**有出处的建议**，不是一句“IFAM 更好”。

**第二层：MCP 负责“真的跑”**

在用户本地或受控算力上，Agent 调用经过验证的工具：

1. `ifam_inspect_inputs`：检查 PLINK bed/bim/fam、表型 ID 对齐、注释文件格式和 split 泄漏；
2. `ifam_fit`：异步调用官方 `IFAM.R` 与 HIBLUP，返回方差组分、预测值和运行日志；
3. `ifam_job_status`：查询作业阶段、错误和产物；
4. `ifam_export`：只导出标准化预测和 provenance，供独立评测使用。

这里没有 `ifam_prepare_annotations`，也没有 `ifam_compute_pearson`。注释目录由调用方准备；上游 `IFAM.R` 会自动发现目录下所有 `*.txt`，不读取清单文件。**Pearson r、AUC 和 prediction bias 由独立 runner 在固定验证集上计算**，不由 IFAM 的包装代码计算，MCP 也不接收 held-out truth。

**第三层：Benchmark 负责“这个数字能不能信、能不能比”**

- 固定数据版本、划分文件、指标定义和重复次数；
- 记录 run ID、代码 commit、容器 digest、数据校验和、环境、日志、预测文件；
- 如果使用论文原始数据和划分，标记为论文精确复现；如果使用我们的开放协议，标记为 L1；
- 如果是论文报告但未复现，标记为 L3，仅作参考，不参与主榜排名。

最终，用户得到的不是“一个分数”，而是：

> “在你的数据上，IFAM 相对 GBLUP 的提升方向/幅度；这个结果与论文设置的差异；以及一个可以复查、可以引用、可以提交审阅的运行记录。”

这就是从“展示评测”到“给研究赋能”的区别。

### 2.3 为什么不能把评测塞进 MCP

Paper2MCP 明确要求：**benchmark 的重算不能放在生产包装里**。原因是：

- 包装者可能无意中改变验证集、缺失值处理或指标实现；
- 作者代码里的“评估脚本”往往与其论文的划分强绑定，不适合作为公共评测；
- 一旦评测逻辑分散在几十个 MCP 里，排行榜就失去了统一口径；
- 评测逻辑必须可审计、可版本化、可单独测试。

因此，正确分工是：

```text
MCP：产生预测、模型参数、诊断信息和日志
独立 harness：读取预测 + 固定验证集 + 统一 metric → 生成 run manifest
站点：只展示 harness 认证过的 run manifest
```

---

## 3. 产品：除了榜单，还能提供什么

### 3.1 研究生命周期的六个环节

当前静态站覆盖的是最后一环“比较”。真正的研究赋能应该覆盖整条链路：

```text
发现论文 → 读懂/选型 → 在自有数据上试跑 → 对齐评测 → 留下证据 → 投稿/认证
  图书馆      Skill         MCP              Benchmark      Evidence      Ecosystem
```

| 产品面 | 用户任务 | 交付物 | 现在 | 后续 |
| --- | --- | --- | --- | --- |
| **论文图书馆** | 快速判断一篇 GSGP 论文值不值得读、能不能用 | 方法护照：输入模态、假设、数据要求、指标、限制、复现等级 | IFAM 阅读包预览 | 其他论文的 Paper2Skill 审校包 |
| **选型顾问** | “我的数据适合哪个方法？” | 有引用的建议 + 实验设计草案 | 研究台预览 | 领域 Agent + 论文 Skill |
| **在自有数据上运行** | 不想配环境，想直接试跑 | 本地/远程 MCP 调用、输入校验、运行日志 | IFAM MCP 本地 stdio 原型，无部署端点 | IFAM MCP 试点与独立验证 |
| **证据账本** | 复查一个数字是怎么来的 | run manifest、划分文件、commit、镜像、日志 | 第一条真实 GBLUP EXP 记录 + result schema | 多 split、审核流水线与更完整 manifest |
| **投稿与认证** | 作者希望方法被认证、被看到 | 提交表单、自动检查、复现、人工审核、认证徽章 | 方案 | GitHub 表单 + 审核流水线 |
| **教学与团队知识库** | 学生/团队复用方法 | 教程、最小 fixture、可运行 notebook | IFAM Skill 预览 + 合成夹具 | 与论文 Skill 共用 |

### 3.2 三个真实用户旅程

**A. 育种数据科学家（最需要“在自有数据上跑”）**

1. 在站内比较 GBLUP / BayesB / IFAM 的公开数据结果；
2. 打开 IFAM 方法护照，看到输入要求、注释依赖、Duroc 论文结果和限制；
3. 用本地 MCP 检查自己的 PLINK 文件，跑一个 5K SNP 的 fixture；
4. 通过后跑全量，得到预测值和诊断；
5. 用站内的评测模板（或自己的验证集）计算指标；
6. 生成一份带 run ID 的方法段落，写进报告或论文。

价值：把“读论文 + 配环境 + 调参 + 写方法”从数周压缩到数天，而且每一步有证据。

**B. 论文作者（最需要“被认证、被复用”）**

1. 通过 GitHub 表单提交论文、代码、许可证和数据说明；
2. 自动检查：仓库可克隆、依赖可安装、许可证允许、示例数据可用；
3. 维护者用 Paper2Skill 构建论文包，用 Paper2MCP 构建 MCP；
4. 独立验证者在全新环境运行示例，确认工具绑定和输出；
5. 在开放数据上跑 L1；如果数据受限，只展示 L3 论文值和明确的不可比说明；
6. 通过人工审核后，获得“已认证论文包 / 已验证 MCP / L1 复现”徽章。

价值：作者获得的是可验证的采用，而不是一次性的引用。

**C. 审稿人/学生（最需要“读懂并解释”）**

1. 问“这篇论文的增益主要来自哪类注释？”；
2. Skill 返回带页码/图表依据的回答，并指出补充材料中的限制；
3. 问“为什么不能把 SBayesRC 和 GBLUP 放在同一张榜上？”；
4. 系统解释输入模态、数据泄漏风险和 L1/L2/L3 的区别；
5. 生成一段可直接放进综述或审稿意见的说明。

价值：把“读论文”从个人经验变成可复查的领域知识服务。

### 3.3 当前站点哪些是真的，哪些是预览

当前 `site/index.html` 已经实现：

- 三列多选（最多 4 个算法、3 个数据集）、搜索、清空、URL 状态；
- 算法卡 Paper / Skill / MCP 证据链：论文 DOI 可打开，缺项明确显示“未上传 / 未认证”，悬浮、键盘聚焦、触屏点按均显示原因；
- Pearson r / R² / AUC / 运行时间切换；
- 分组柱状图、误差条、L1/L3 视觉区分、结果矩阵、运行详情抽屉；
- 证据轨道、图表注、移动端重排、键盘焦点管理；
- 学术期刊风格的视觉系统与 MIT 归属页脚。

当前**已有但尚未认证**：

- IFAM 的 Paper2Skill 包（`agents/ifam/skill/ifam-paper/`，`reviewed_with_limitations`）；
- IFAM MCP 契约草案（4 个工具）与合成 tiny fixture；
- 站内 IFAM Skill 阅读预览（`site/resources/ifam-paper/`）。

当前**没有**实现：

- 任何真实 MCP 端点；所有算法卡仍标注“MCP 未认证”，IFAM 只是首批试点；
- IFAM 之外的 Paper2Skill 包；其他算法卡仍标注“Skill 未上传”；
- 任何实时运行或实时评测；页面评测数值仍为演示值；
- 真实认证数据；
- 用户数据上传或账号系统。

> 阅读包不是复现结果；契约和夹具也不是可调用服务。两者的状态分别以
> `reviewed_with_limitations` 和 `draft / 本地原型 / 未认证` 为准。

研究台里的话是产品契约，不是上线声明。页面上已经明确标注 “Demo data / Preview / 未上线”，后续真实结果接入时必须继续保留这种区分。

---

## 4. 目标架构

### 4.1 分层

```text
┌──────────────────────────────────────────────────────────────┐
│ 客户端：Claude Code / Cursor / GSGP Research Console / API    │
└──────────────────────────────┬───────────────────────────────┘
                               │ MCP（stdio 或 Streamable HTTP）
┌──────────────────────────────▼───────────────────────────────┐
│ Agent 层：Skill 路由 + 工作流提示词 + 权限/预算/审计           │
│  - 先读方法护照，再决定是否运行                                │
│  - 需要运行 → 调用 MCP；只需要解释 → 只读 Skill                │
└───────────────┬──────────────────────────────┬───────────────┘
                │                              │
┌───────────────▼──────────────┐  ┌────────────▼───────────────┐
│ Skill Registry                │  │ MCP Registry               │
│ 审校后的论文知识包、方法护照   │  │ 每个方法一个版本化容器      │
│ 引用、限制、示例、术语表       │  │ tools/resources/prompts     │
└───────────────┬──────────────┘  └────────────┬───────────────┘
                │                              │ 长任务提交
                │                  ┌───────────▼───────────────┐
                │                  │ 计算平面（非 Cloudflare）  │
                │                  │ R / HIBLUP / GCTB / PLINK │
                │                  │ 队列、容器、配额、日志      │
                │                  └───────────┬───────────────┘
                │                              │ 预测/日志/产物
                │                  ┌───────────▼───────────────┐
                │                  │ 独立评测 harness            │
                │                  │ 固定数据 + 划分 + evaluate  │
                │                  └───────────┬───────────────┘
                │                              │ run manifest
                │                  ┌───────────▼───────────────┐
                └─────────────────▶│ Evidence Registry          │
                                   │ 结果 JSON、哈希、状态、审计  │
                                   └───────────┬───────────────┘
                                               │ 构建
                                   ┌───────────▼───────────────┐
                                   │ 静态发布（Cloudflare Pages）│
                                   │ 榜单、方法护照、证据页       │
                                   └───────────────────────────┘
```

### 4.2 各层职责与边界

| 层 | 可以做什么 | 明确不做什么 |
| --- | --- | --- |
| 客户端 | 自然语言交互、调用 MCP、展示结果 | 不直接执行论文代码 |
| Agent 层 | 选择 skill/MCP、编排工作流、解释结果 | 不替代独立评测，不制造数据 |
| Skill Registry | 提供审校知识、引用、限制、模板 | 不执行代码 |
| MCP Registry | 暴露经过验证的工具和资源 | 不计算公共榜单指标，不保存受限数据 |
| 计算平面 | 运行官方代码、产生预测和日志 | 不直接对外提供匿名任意代码执行 |
| 评测 harness | 统一定义指标、读取固定验证集 | 不接受作者自定义的指标实现 |
| Evidence Registry | 保存 run manifest、版本、审计 | 不混排 L1/L3，不覆盖历史 |
| 静态站 | 展示、筛选、解释、分享 | 不承担 R/GCTB 计算，不存密钥 |

### 4.3 Cloudflare 的位置

Cloudflare Pages 适合：

- 静态页面、榜单、方法护照、说明文档；
- 从已提交的 JSON 构建；
- 预览部署、回滚、缓存。

Cloudflare **不适合**：

- 运行 R、HIBLUP、GCTB、PLINK；
- 执行任意论文代码；
- 保存 UKB/WTCCC 等受限数据；
- 承载长时间、大内存的拟合任务。

如果未来需要轻量 API，可以让 Cloudflare Workers 负责鉴权、提交任务、查询状态，但真正的计算必须在独立容器/队列中完成。这个边界建议写进架构决策，避免后期“顺手把算法放进 Worker”。

### 4.4 GSGP MCP 的接口设计原则

1. **工具按“可独立完成的任务”划分，不按脚本行数划分。**  
   例如 `ifam_fit` 是有意义的；`run_line_12_of_script` 不是。
2. **长任务使用 job 模式。**  
   `submit` 返回 job_id，`status` 查询进度，`collect` 取结果。不要让一个 HTTP 请求挂 40 分钟。
3. **输入先校验，后计算。**  
   PLINK 文件、表型 ID、注释版本、染色体命名、缺失值阈值都要显式检查。
4. **输出必须结构化。**  
   预测值、方差组分、诊断、日志路径、输入哈希都以 schema 约束的 JSON 返回。
5. **生产包装不实现评测指标。**  
   评测由独立 harness 完成。
6. **工具版本与论文版本绑定。**  
   `ifam@1.0.0+hiblup@1.1.0` 这样的组合要有 manifest；升级要重新验证。
7. **默认不联网、不挂载敏感目录、不执行用户任意脚本。**  
   输入通过受控挂载或对象存储进入，输出写到隔离目录。
8. **每个工具都能回答“你调用的是哪段源代码”。**  
   至少记录仓库、commit、文件路径、函数名；这是可信度的基础。

### 4.5 数据边界

| 数据类型 | 站点展示 | MCP 默认位置 | 备注 |
| --- | --- | --- | --- |
| 开放数据（1000G、Duroc、公开汇总统计） | 可展示结果与元数据 | 可托管运行 | 仍需遵守原始许可证 |
| 需申请数据（UKB、WTCCC、IRRI 水稻等） | 只展示论文报告值/L3 | 不上传、不托管 | 用户如获授权，只能在自己的受控环境运行 |
| 私有育种数据 | 不展示 | 本地或用户自己的云 | 默认“数据不出域” |
| 论文 PDF/补充材料 | 在许可允许时展示知识包/引用 | 可作为资源 | 不重新分发受限附件 |
| 运行日志/预测 | 只展示认证后的聚合结果 | 受控存储 | 不包含个体级敏感数据 |

---

## 5. MCP 稳定性与可信度工程

会议纪要里对 MCP 不稳定的担忧是对的。Paper2Agent 的 593/599 自动验证通过，说明“构建时可用”已经可以做到；但“明年还能跑”是另一件事。稳定性要按产品来做，而不是按 demo 来做。

### 5.1 失败模式与对策

| 失败模式 | 典型原因 | 工程对策 | 用户看到什么 |
| --- | --- | --- | --- |
| 环境漂移 | R 包升级、HIBLUP 版本变化、系统库缺失 | 锁定版本、容器 digest、定期重建 | “该 MCP 版本已暂停认证，原因…” |
| 输入不合法 | PLINK 染色体命名、ID 不匹配、注释版本不对 | 前置校验、明确错误码、示例输入 | “第 3 号染色体的 SNP 不在注释中，请检查…” |
| 运行超时/OOM | 全量 UKB 级数据、LD 矩阵过大 | 任务队列、资源上限、分块、预估 | “预计需要 X GB 内存；建议先跑 fixture” |
| 工具实现偏差 | 包装层偷偷改了默认参数 | 独立验证、参考输出对比、代码审查 | 验证报告 + 限制说明 |
| 结果不可比 | 不同划分、不同指标、不同输入模态 | 评测 harness + L1/L2/L3 + 提示 | “L2：输入模态不同，不参与主榜排名” |
| 服务不可用 | 托管平台故障、网络问题 | 健康检查、重试、降级到本地 CLI/Skill | “MCP 暂不可用；可以先阅读方法护照或使用本地 CLI” |
| 许可问题 | 代码许可不清、数据不可再分发 | 提交时检查许可证；发布前人工复核 | 不展示或只展示元数据 |
| 科学错误 | 方法本身不适用于该性状 | 领域审核、限制说明、失败案例 | “该配置不推荐；原因…” |

### 5.2 认证清单

一个 MCP 只有全部通过以下检查，才能进入“已验证”区：

- [ ] 许可证允许使用与再分发（代码、模型、示例数据分别核对）；
- [ ] 工具绑定到真实源代码，有文件路径和 commit；
- [ ] 在干净环境中能从零安装；
- [ ] 在全新位置启动 server，工具清单和 schema 可读；
- [ ] 示例输入产生与参考实现一致的输出（在容差内）；
- [ ] 至少一个“改变输入”的验收调用通过；
- [ ] 失败输入有清晰错误，不崩溃、不静默；
- [ ] 超时、内存、并发和输出大小有上限；
- [ ] 不包含受限数据、密钥、个人身份信息；
- [ ] 生产包装不计算 benchmark 指标；
- [ ] 独立验证者签字，限制写入文档；
- [ ] 版本、镜像 digest、依赖锁定，并有复验日期。

### 5.3 运行指标（建议目标，不是承诺）

- 认证 MCP 在标准 fixture 上的启动成功率 ≥ 99%；
- 认证工具在验收用例上的成功率 ≥ 99%；
- 每次运行都有 run manifest 和日志；
- 失败运行也有可读的失败原因，不允许“空白”；
- 每次发布都可回滚到上一个认证版本；
- 每个认证 MCP 至少每季度复验一次，依赖升级后立即复验。

### 5.4 人机边界

- **自动检查**负责：可安装、可启动、schema、参考输出、资源限制、许可证字段。
- **领域审核**负责：工具选择是否合理、是否泄漏测试数据、指标是否被改变、结论是否被过度解释。
- **作者**负责：原始代码和数据的正确性。
- **平台**负责：协议、可追溯性、展示与纠错，不替作者背书科学结论。

---

## 6. 两篇测试论文的复现评估

### 6.1 先把“复现”拆开

“复现”在论文语境里至少有五种含义，混在一起会误导用户。建议本站固定使用以下分级：

| 代号 | 含义 | 本站标签 | 能否排名 |
| --- | --- | --- | --- |
| **R0** | 论文知识包：正文、补充材料、图表被审校并可检索 | Paper Skill | 不适用 |
| **R1** | 参考执行：官方代码在论文示例/fixture 上跑通 | MCP validated | 不适用 |
| **R2** | 方法级复现：在**我们的开放数据与协议**上跑通并评测 | **L1** | 是（同协议内） |
| **R3** | 论文表格精确复现：数据、划分、指标、预处理尽量与论文一致 | Paper-exact（单独标记） | 需与本站协议对齐后才可排名 |
| **R4** | 独立扩展：新数据、新人群、新性状 | Exploratory | 否 |

当前站点的 **L1** 对应 R2；**L3** 是“论文报告值”，不是 R3。即便我们真的精确复现了论文表格（R3），也不能自动把它当作本站主榜的 L1，因为本站的划分和指标可能不同。这个区别必须在方法护照和运行详情里写清楚。

### 6.2 IFAM

**论文信息**：Tang et al., *Nature Communications* 2026, DOI [10.1038/s41467-026-72470-0](https://www.nature.com/articles/s41467-026-72470-0)。

**方法要点**：在 GBLUP 基础上引入多个随机效应，把不同功能注释对应的 SNP 组分别建模，并自动合并贡献相近的组；同时纳入与目标性状显著相关的 SNP 组。它面向个体水平基因型 + 表型 + 功能注释。

**论文报告的平均提升（相对 GBLUP）**：

| 数据集 | 平均提升 |
| --- | --- |
| WTCCC1（7 种疾病，AUC） | 9.46% |
| UK Biobank（6 个性状） | 6.15% |
| Duroc 猪 | 4.59% |
| Yorkshire 猪 | 4.09% |
| 3000 水稻 | 10.83% |

论文同时指出：去掉 trait-specific GWAS 注释后，仅功能注释在 UKB 上只带来 1.40% 提升，在牲畜/作物上仅有边际提升。这一条对产品解释非常重要：**IFAM 的增益不是“注释越多越好”的保证，而是依赖注释类型、性状和数据的。**

**代码与数据可得性**：

| 项目 | 内容 | 可得性 |
| --- | --- | --- |
| 官方代码 | [xiaolei-lab/IFAM](https://github.com/xiaolei-lab/IFAM)，MIT | 公开 |
| 论文版本 | Zenodo [10.5281/zenodo.18802709](https://doi.org/10.5281/zenodo.18802709) | 公开 |
| 运行依赖 | R、HIBLUP v1.1.0、optparse；PLINK bed/bim/fam | 公开安装 |
| 输入 | PLINK 基因型 + 表型 + 注释 SNP 列表目录 | 由用户准备 |
| WTCCC1 | 受控访问，7 种疾病，约 4.8k/病种，约 450k SNP | 需申请 |
| UK Biobank | 申请号 97563；348,501 名 EUR 无亲缘个体；1,094,840 SNP；6 性状 | 需申请 |
| Duroc | 2,796 头；11.3M SNP；7 个性状；[GigaDB 100894](https://doi.org/10.5524/100894) | **开放** |
| Yorkshire | 表型/部分数据 Figshare；原始基因型 2028-04-01 后 EVA | 部分开放/禁运 |
| 3000 Rice | 3,024 份；333,454 SNP；5 个性状；[IRRI](https://iric.irri.org/projects/3000-rice-genomes-project) | 需申请/获取 |
| 注释 | 人类 RegulomeDB + baselineLD；猪 IFmut；水稻 RAP-DB | 多数公开，需逐项核对许可 |

**可行性判断**：

| 维度 | 判断 | 说明 |
| --- | --- | --- |
| 代码可运行性 | 高 | R 脚本 + HIBLUP，依赖明确；有 demo 数据 |
| 开放数据可行性 | 中高 | Duroc 开放；水稻需申请；其余受限 |
| 论文表格精确复现 | 低～中 | Duroc 有希望做“接近论文设置”的复现；UKB/WTCCC/Yorkshire 现在不可行 |
| 计算量 | 中高 | 全量 Duroc 11.3M SNP × 多随机效应，需足够内存；先 fixtures 再全量 |
| 工程风险 | 中 | R/HIBLUP 环境、注释格式、PLINK 版本、划分泄漏 |
| 产品价值 | 高 | 动物育种用户直接相关；论文新、代码清晰、有开放数据 |

**当前进度（2026-10-18）**

| 交付物 | 状态 | 说明 |
| --- | --- | --- |
| IFAM Paper2Skill | `reviewed_with_limitations` | 13 个文件；0 mechanical issues；6 项来源裁定；9/9 图/公式核对；补充材料缺失已记录 |
| 站点阅读预览 | 已生成 | `site/resources/ifam-paper/`，含 ZIP 与 SHA-256 清单；不是基准证据 |
| 上游归档核对 | 已完成格式校准 | `main.zip` SHA-256 `b66f1a…91bd2b`；commit 与 `IFAM.R` 哈希已记录；demo 表头、注释发现、`anno_spec`、`.rand` 列名已核对；许可 MIT/GPL 冲突待解 |
| MCP 契约 | draft | 4 个工具：inspect、fit、job status、export；export 只导出预测；首批只支持一个特殊注释 |
| tiny fixture | 合成、已按上游校准 | 12×24；注释重叠、缺失基因型、特殊注释与 split；未跑过 IFAM/HIBLUP |
| MCP server | 本地原型 | 4 工具 stdio、tiny 黄金输出、真实 IFAM.R + fake HIBLUP dry-run 已通过；无部署端点、无认证；不接收 held-out truth；真实 HIBLUP 执行验收待 v1.1.0 |
| L1 结果 | 未开始 | 等待 HIBLUP v1.1.0 环境与独立 runner |

**Benchmark/证据层（2026-10-19）**：已完成第一条真实 GBLUP exploratory 记录：
500×5k 上游 demo 基因型 + h²=0.5 模拟性状，单次 80/20 划分，Pearson r 0.508、
R² 0.258。GBLUP 已手动封装为 baseline Skill/MCP；记录由 MCP
（`gblup_inspect_inputs → gblup_fit → gblup_export`）产生，再由独立 runner 评测，
公开记录在 `benchmark/runs/gblup-sim500-mcp-v1/result.json`，站点标为 EXP，不是 L1。
这是 manual baseline，不是 Paper2Agent 自动生成；原始数据与个体预测只在本地，不发布。

**推荐试点范围（IFAM × Duroc）**

目标不是“复现论文所有表格”，而是先回答一个可验证的问题：

> 在我们的开放数据、固定划分和统一指标下，IFAM 相对 GBLUP 是否表现出与论文方向一致的增益？增益幅度和不确定性是多少？

**第一阶段（约 4 周，1 名开发者 + 领域审阅）**：

1. **Paper Skill（已完成，有限制）**：IFAM 论文包已严格校验为 `reviewed_with_limitations`；补充材料缺失已记录。仍需在 Duroc/L1 阶段补充方法护照和论文设置对照。
2. **最小 fixture（契约级已完成，执行级待办）**：12×24 合成夹具已按 `IFAM.R` 1.0.0 的注释发现规则和 `anno_spec` 语义校准；下一步从 Duroc 抽取 200–500 头 × 5K–50K SNP，跑通 `IFAM.R` + HIBLUP，记录耗时和内存。
3. **MCP 包装（draft）**：首批 4 个工具（校验、拟合、状态、导出）；独立验证者在全新环境跑夹具和至少一个改变输入的用例。导出只交接预测，指标由独立 runner 计算。
4. **L1 评测**：全量 Duroc 或一个明确限定的子集；先固定 5 次 80/20 重复（论文用 20 次；5 次是成本折中，需在方法护照中说明）；比较 GBLUP / BayesB / IFAM；由独立 harness 计算 Pearson r；报告均值 ± 标准差。
5. **证据与展示**：生成 run manifest；把站点中 Duroc 的演示值替换为真实 L1 值；保留 L3 论文值作为参考并明确区分。
6. **人工审核**：领域审阅者检查划分、注释、泄漏、指标和结论措辞。

**技术要点：trait-specific SNP 不能泄漏测试集。**  
如果 IFAM 的输入包含“与性状显著相关的 SNP 列表”，这个列表必须在训练折内生成，或在划分之前由独立于验证集的数据产生。用全量数据做关联再划分，会把验证集信息带进模型，导致虚高。这是本项目相对于“直接跑作者脚本”的关键增值点，也是方法护照必须写清楚的内容。

**建议的 MCP 工具面（先少后多）**：

- `ifam_inspect_inputs`：检查 PLINK、表型、注释目录、ID 对齐与 split 泄漏；
- `ifam_fit`：异步调用官方 `IFAM.R`，返回作业 ID；用 `ifam_job_status` 轮询；
- `ifam_export`：导出标准化预测结果、split 元数据与 provenance（不计算 Pearson/AUC，不接收 truth）。

`ifam_prepare_annotations` 不在首批：上游 `IFAM.R` 直接扫描目录下所有 `*.txt`，不需要额外清单；包装层只需校验文件名、列数和 SNP 是否在 `.bim` 中。首批 `special_annotations` 只支持一个 stem，因为上游 1.0.0 的多值路径有 bug。

**验收标准**：

- fixture 上的预测与参考运行在容差内一致；
- MCP 在全新环境启动并通过验收调用；
- 至少一个错误输入返回可读错误；
- L1 结果有 run ID、数据哈希、划分哈希、commit、环境、日志；
- 站点不出现“论文全部复现”的表述；
- 不包含 UKB/WTCCC/Yorkshire 原始数据。

**风险与应对**：

- 全量 Duroc 下载和存储较大：先确认磁盘/带宽，再下载；用校验和验证。
- 多随机效应拟合可能比预期慢：先测单次耗时，再决定重复次数；必要时缩小 SNP 集并明确标注。
- 注释版本不一致：锁定来源、版本、下载日期和文件哈希。
- 论文的提升幅度在我们划分下可能更小或不显著：如实报告，不调整划分“找显著”。
- R/HIBLUP 依赖漂移：容器化 + digest 锁定 + 复验。

**可以对外说什么（复现完成后）**：

- ✅ “在 Duroc 公开数据上，按 GSGP-Bench 协议完成了 IFAM 与 GBLUP 的 L1 对比。”
- ✅ “论文报告值为 L3 参考；我们的数值与论文设置的差异见方法护照。”
- ❌ “完整复现了 IFAM 论文在 WTCCC1/UKB/Yorkshire 上的结果。”
- ❌ “IFAM 在所有数据上都能提升 4.59%。”

### 6.3 SBayesRC

**论文信息**：Zheng et al., *Nature Genetics* 2024, DOI [10.1038/s41588-024-01704-y](https://www.nature.com/articles/s41588-024-01704-y)。

**方法要点**：使用 GWAS 汇总统计 + LD 参考 + 功能注释，在约 7M 常见 SNP 和 96 个注释上建模；注释同时影响因果变异概率和效应分布。相对不使用注释的 SBayesR，论文报告欧洲人群约 14% 提升，跨祖先最高约 34%。

**代码与数据可得性**：

| 项目 | 内容 | 可得性 |
| --- | --- | --- |
| 官方代码 | [zhilizheng/SBayesRC](https://github.com/zhilizheng/SBayesRC) + [GCTB](https://cnsgenomics.com/software/gctb/#Download) | 公开 |
| 论文版本 | Zenodo [10.5281/zenodo.10416921](https://doi.org/10.5281/zenodo.10416921) | 公开 |
| 运行方式 | R 包；官方提供 Docker 镜像 `zhiliz/sbayesrc`（x86_64） | 公开 |
| 输入 | COJO 格式 GWAS summary + LD reference + annotation 文件 | 资源可下载/需核对许可 |
| 论文核心数据 | UKB、UK10K、LifeLines | 需申请 |
| 公开替代 | 1000G、FinnGen、BBJ、PAGE 等汇总数据 | 公开/需遵守条款 |
| 验证数据 | UKB 341,809 名 EUR 个体，10 折 CV | 需申请 |

官方 README 提供了下载 LD reference 和 annotation 的 Resources 说明，以及 Docker 用法。这使“R1 + 公开数据 L2 试点”比想象中更可行；但它**不能**替代论文中受限的验证数据和精确设置。

**可行性判断**：

| 维度 | 判断 | 说明 |
| --- | --- | --- |
| 代码可运行性 | 中高 | R 包 + GCTB；有 Docker；输入格式要求明确 |
| 开放数据 L2 可行性 | 中 | 1000G 仿真 + 公开 summary/LD/注释可做；需仔细设计 summary 生成和验证 |
| 论文表格精确复现 | 低 | UKB/UK10K/LifeLines 受限；跨祖先需要匹配的 LD 和验证集 |
| 计算量 | 高 | ~7M SNP、96 注释、LD 矩阵；内存和 I/O 重 |
| 工程风险 | 高 | summary QC、LD 对齐、注释版本、收敛、长任务 |
| 产品价值 | 高 | 人类复杂性状/PRS 用户核心方法；代表“汇总统计”路线 |

**推荐第二阶段范围（SBayesRC × 1000G 仿真/公开汇总）**

目标：

> 在完全公开的数据上，验证 SBayesRC 相对 SBayesR 的注释增益方向，并建立一条可复用的“summary → LD → PRS → 验证”流水线；不承诺复现论文的 14%。

**建议路径**：

1. **Paper Skill**：审校 SBayesRC 的模型、输入格式、LD/注释版本、CV 设置、跨祖先限制；产出方法护照。
2. **数据方案 A（推荐先做）**：1000G EUR 基因型 + 模拟表型 → 在训练折内生成 GWAS summary（PLINK/REGENIE）→ 用官方 LD/注释运行 SBayesRC 与 SBayesR → 在独立验证集计算 R²/相对准确率。标注为 **L2**（输入模态不同）。
3. **数据方案 B（可选）**：公开 summary（如 FinnGen/BBJ/PAGE 中许可清晰、祖先匹配的性状）+ 公开 LD + 官方注释；验证集使用 1000G 仿真或公开个体数据。注意 summary 的样本重叠和祖先匹配。
4. **小规模 fixture**：先单染色体或 HapMap3 子集跑通；再扩展到全基因组；记录内存、耗时、收敛情况。
5. **MCP 包装**：`sbrc_validate_inputs`、`sbrc_prepare_annotations`、`sbrc_run`（job）、`sbrc_collect`、`sbrc_prs`；长任务必须异步。
6. **证据**：由独立 harness 计算验证集指标；论文值保持 L3；公开 pilot 标注 L2/探索性。

**为什么不能把它标成 L1**：

- SBayesRC 使用汇总统计 + LD，而不是个体水平基因型；与 GBLUP/IFAM 的输入模态不同；
- 用训练折生成的 summary 与个体水平方法的“同一数据”并不等价；
- 跨祖先需要目标人群的验证数据和匹配 LD，当前公开资源不足以复现论文结论。

因此，正确的展示是：**同数据来源、同划分、不同输入模态的 L2 探索**，而不是与 L1 方法混排。

**风险与应对**：

- LD/注释资源版本变化：锁定下载版本和哈希；保留资源清单。
- summary 质控不当：先做 allele、MAF、样本量、基因组构建对齐；记录过滤步骤。
- 计算资源不足：先 HapMap3/单染色体，逐步扩展；设置内存上限和超时。
- 收敛问题：记录诊断，不隐藏失败；失败也是证据。
- 许可不清：只使用许可明确的公开 summary；不下载/上传 UKB/UK10K/LifeLines。
- 过度解释：不把模拟结果外推到真实人群；不宣称实现论文的 14%/34%。

### 6.4 两篇论文的对比

| 维度 | IFAM | SBayesRC |
| --- | --- | --- |
| 输入模态 | 个体基因型 + 表型 + 注释 | GWAS summary + LD + 注释 |
| 官方实现 | R + HIBLUP | R + GCTB；有 Docker |
| 开放数据 | Duroc 开放；水稻需申请 | 1000G/公开 summary 可用 |
| 受限数据 | UKB、WTCCC、Yorkshire | UKB、UK10K、LifeLines |
| 精确复现难度 | 中（Duroc 有希望） | 高（核心验证数据受限） |
| 计算强度 | 中高 | 高 |
| 首次试点 | **优先** | 第二阶段 |
| 本站等级 | L1（R2）可争取 | L2（探索）先做 |
| 主要风险 | 注释/划分泄漏、R 环境 | LD/注释对齐、summary 质控、长任务 |

### 6.5 数据与下载清单

在批准试点前，不需要下载全量数据。建议按以下顺序：

| 优先级 | 资产 | 用途 | 获取方式 | 备注 |
| --- | --- | --- | --- | --- |
| P0 | IFAM 官方仓库 + demo_data | R1 参考执行 | GitHub | 小，先跑通 |
| P0 | Duroc 小样本 fixture | MCP/fixture | 从 GigaDB 下载后抽样 | 需校验和 |
| P0 | HIBLUP v1.1.0、R、PLINK | 运行环境 | 官方安装 | 容器化 |
| P1 | Duroc 全量基因型/表型/注释 | L1 评测 | [GigaDB 100894](https://doi.org/10.5524/100894) | GB 级；先确认磁盘/带宽 |
| P1 | IFmut / RegulomeDB / baselineLD / RAP-DB 注释 | IFAM 输入 | 官方数据库 | 逐项核对许可与版本 |
| P2 | 3000 Rice Genomes | 扩展 | [IRRI](https://iric.irri.org/projects/3000-rice-genomes-project) | 需申请 |
| P2 | 1000G 参考基因型 | SBayesRC 仿真/LD | 1000G 官网 | 公开 |
| P2 | SBayesRC LD/注释资源 | L2 pilot | 官方 Resources | 锁定版本 |
| P2 | 公开 GWAS summary（FinnGen 等） | 可选 L2 | 各项目官网 | 核对许可和祖先 |

**绝对不要**下载后上传到公开仓库或站点：UK Biobank、WTCCC1、Yorkshire 原始基因型、UK10K、LifeLines，以及任何个体级私有数据。即使用户有合法访问权，公开主榜也只能展示聚合指标和论文报告值。

### 6.6 话术规范

建议把以下句式写进方法护照和网站说明：

- ✅ “这是在我们的开放数据与协议下的 L1 复现；与论文原始表格的差异见说明。”
- ✅ “这是 L3 论文报告值，未在本站复现，不参与主榜排名。”
- ✅ “这是 L2 探索：输入模态与个体水平方法不同，不能直接比较。”
- ✅ “该 MCP 已通过 fixture 和运行时验证；全量数据上的表现仍需复现。”
- ❌ “完全复现了论文。”
- ❌ “我们的结果证明该方法普遍更优。”
- ❌ 把不同数据、不同划分、不同输入模态的数字放在同一张排名表里。

---

## 7. 路线图与验收

### 7.1 分阶段

| 阶段 | 时间 | 交付 | 退出条件 |
| --- | --- | --- | --- |
| **Phase 0：形态与论证（当前）** | 已完成 | 学术风格站点、产品评估、复现方案 | 站点可演示；文档可评审 |
| **Phase 1：IFAM 纵向打通** | 约 4 周 | IFAM 论文 Skill、MCP（4 工具）、Duroc fixture、L1 结果、方法护照 | 参考执行、MCP 独立验证、L1、人工审核全部通过 |
| **Phase 2：公开数据扩展** | 约 4 周 | Duroc 全量/水稻（若获数据）、SBayesRC L2 pilot、长任务运行时 | 两个 MCP、至少 2 个真实 L1/L2 单元、站点换成真数据 |
| **Phase 3：认证与研究台** | 约 4 周 | 投稿表单、认证流程、研究台真实问答、多论文 Agent | 首个外部提交完成审核；研究台可回答真实问题 |

### 7.2 阶段闸门

对每篇论文，统一使用：

- **G0 许可与来源**：代码、数据、注释、模型许可清晰；
- **G1 知识包**：Paper2Skill 严格验证通过，限制写明；
- **G2 参考执行**：官方代码在 fixture 上跑通，结果可复现；
- **G3 MCP 验证**：独立验证者 + 全新运行时 + 至少一个新输入；
- **G4 协议评测**：独立 harness 产出 L1/L2，run manifest 完整；
- **G5 人工审核**：领域审阅者确认结论措辞；
- **G6 发布**：站点展示、方法护照、证据页、回滚路径。

### 7.3 衡量指标

不要只统计“接入了多少论文”。更有意义的指标：

- 从“提交论文”到“首个可运行 MCP”的时间；
- 从“用户数据”到“首个可信结果”的时间；
- 认证 MCP 的 90 天复验通过率；
- L1/L2/L3 单元数量，以及被人工复核的比例；
- 每个结果可追溯字段的完整率（目标 100%）；
- 领域问答的引用准确率（建议用 20–30 个固定问题集）；
- 外部用户完成一次真实运行的转化率；
- 因失败/不可比而下架或降级的比例（这应该被公开，而不是隐藏）。

### 7.4 成本与团队

- 论文转换的边际成本参考论文：简单案例约 US$13–14、45 分钟；但 GSGP 的全量数据和 R/GCTB 运行成本显著更高，必须在真实数据上测一次再估算。
- 团队最小配置：1 名全栈/基础设施开发者 + 1 名 GSGP 领域审阅者 + 可用的 CPU 计算资源；GPU 不是第一阶段的必需品（IFAM/SBayesRC 主要吃 CPU/内存）。
- 计算建议：fixture 在本地；全量运行在实验室服务器或云上批处理；静态站和元数据在 Cloudflare；不要用 Cloudflare Workers 跑算法。
- 存储：基因型、LD、注释、预测和日志分开管理；受限数据只进受控环境，不进公开对象存储。

### 7.5 关键决策点

1. **试点范围**：建议先 IFAM × Duroc，不要同时开两条重工程线；SBayesRC 在 Phase 2 做可行性 spike。
2. **算力位置**：建议“本地/实验室服务器优先，云端批处理补充”；不要在 Cloudflare Worker 中执行 R/GCTB。
3. **私有数据策略**：建议默认“数据不出域”，只提供本地 MCP/CLI；平台托管只处理开放数据和认证后的聚合结果。
4. **认证标准**：建议把“代码可运行、MCP 已验证、L1 可复现、论文值可追溯”拆成独立徽章，而不是一个模糊的“已认证”。

---

## 8. 附录

### 8.1 术语

- **MCP（Model Context Protocol）**：让 Agent 以标准方式发现和调用外部工具/资源的协议。
- **Tool**：MCP 暴露的可执行函数，带输入/输出 schema。
- **Resource**：MCP 暴露的静态内容（文档、数据字典、示例）。
- **Prompt**：MCP 提供的多步工作流模板。
- **Paper Skill**：经过审校的论文知识包，供 Agent 阅读、引用和规划。
- **Paper MCP**：把论文官方代码包装成经过验证的 MCP server。
- **L1 / L2 / L3**：本站的可比性等级；L1 为同协议复现，L2 为同数据不同输入/设置，L3 为论文报告值。
- **run manifest**：一次运行的完整档案，含代码、环境、数据、划分、指标、日志和产物。

### 8.2 最小 run manifest 示例

```json
{
  "run_id": "ifam-duroc-bf-20261018-001",
  "paper": {
    "id": "ifam",
    "doi": "10.1038/s41467-026-72470-0",
    "repo": "https://github.com/xiaolei-lab/IFAM",
    "commit": "<git-sha>"
  },
  "method_version": "ifam@1.0.0+hiblup@1.1.0",
  "container_digest": "sha256:...",
  "dataset": {
    "id": "duroc",
    "version": "v1",
    "sha256": "...",
    "access": "open"
  },
  "split": {
    "file": "splits/duroc-bf-80-20-repeat5.json",
    "sha256": "...",
    "scheme": "repeated 80/20 x5"
  },
  "metric": {
    "name": "pearson_r",
    "implementation": "benchmark/evaluate.py@<sha>",
    "value": null,
    "sd": null
  },
  "status": "pending_evaluation",
  "artifacts": {
    "predictions": "artifacts/.../predictions.tsv",
    "log": "artifacts/.../run.log"
  },
  "review": {
    "reviewer": null,
    "reviewed_at": null,
    "limitations": []
  }
}
```

说明：`metric.value` 只能由独立 harness 写入；MCP 只产出预测和日志。

### 8.3 MCP 工具契约示例（IFAM）

```yaml
name: ifam-mcp
version: 1.0.0
source:
  repo: https://github.com/xiaolei-lab/IFAM
  commit: 62f8e4cd8ee53d70b3324ec5cd40d3f2ffbf7649
  license: MIT (repository LICENSE; Scripts/IFAM.R header says GPL-3.0 — unresolved)
runtime:
  image: ghcr.io/<org>/ifam-mcp@sha256:<digest>
  command: python -m ifam_mcp.server
tools:
  - name: ifam_inspect_inputs
    description: Validate PLINK, phenotype, auto-discovered annotation *.txt files and split.
    input_schema: ...
    output_schema: ...
  - name: ifam_fit
    description: Run the pinned official IFAM.R 1.0.0 and HIBLUP v1.1.0; at most one special annotation.
    input_schema: ...
    output_schema: ...
  - name: ifam_job_status
    description: Poll state, phase, errors and artifacts.
    input_schema: ...
    output_schema: ...
  - name: ifam_export
    description: Export predictions and provenance; never computes benchmark metrics.
    input_schema: ...
    output_schema: ...
prohibited:
  - computing leaderboard metrics
  - accepting held-out truth
  - downloading restricted data
  - executing arbitrary user scripts
```

### 8.4 资料来源

- Paper2Agent 论文：[Reimagining research papers as interactive and reliable AI agents](https://www.nature.com/articles/s41586-026-11044-y)，*Nature*，DOI 10.1038/s41586-026-11044-y。
- Paper2Agent 仓库：[jmiao24/Paper2Agent](https://github.com/jmiao24/Paper2Agent)，MIT。
- IFAM 论文：[Improving genomic prediction accuracy of complex traits by integrating massive types of functional annotation information](https://www.nature.com/articles/s41467-026-72470-0)，*Nature Communications*，DOI 10.1038/s41467-026-72470-0。
- IFAM 代码：[xiaolei-lab/IFAM](https://github.com/xiaolei-lab/IFAM)，仓库 LICENSE 为 MIT；`Scripts/IFAM.R` 文件头写 GPL-3.0，冲突待核，未再分发。
- Duroc 数据：[GigaDB 100894](https://doi.org/10.5524/100894)。
- 3000 Rice Genomes：[IRRI](https://iric.irri.org/projects/3000-rice-genomes-project)。
- SBayesRC 论文：[Leveraging functional genomic annotations and genome coverage to improve polygenic prediction of complex traits within and between ancestries](https://www.nature.com/articles/s41588-024-01704-y)，*Nature Genetics*，DOI 10.1038/s41588-024-01704-y。
- SBayesRC 代码：[zhilizheng/SBayesRC](https://github.com/zhilizheng/SBayesRC)。
- GCTB 下载与资源：[cnsgenomics.com/software/gctb](https://cnsgenomics.com/software/gctb/#Download)。
- 论文版本的 Zenodo：[IFAM](https://doi.org/10.5281/zenodo.18802709)、[SBayesRC](https://doi.org/10.5281/zenodo.10416921)。

---

## 9. 一页总结

- Paper2Agent 的可借鉴核心是“论文 → 绑定真实代码的 MCP → 独立验证 → 可追溯”，不是让 LLM 自由生成算法。
- Skill 让 Agent 懂论文，MCP 让 Agent 跑方法，Benchmark 让数字可比；三者分工不能混。
- 静态站是发布层，不是全部产品；研究基础设施要覆盖“发现、理解、试跑、评测、认证”。
- IFAM 是第一条最合适的纵向试点：代码开放、Duroc 数据开放、方法价值明确；先做 fixture，再做 Duroc L1，不碰受限数据。
- SBayesRC 放第二阶段：先做 1000G 仿真 + 公开 LD/注释的 L2 探索，不宣称复现论文的 14%/34%。
- 所有展示都必须区分 L1 / L2 / L3、demo / real、validated / unreviewed；没有证据的数字，不配上主榜。

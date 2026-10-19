# IFAM MCP 工具契约（草案）

状态：**draft / 本地 stdio 实现 / 未认证**。本文件定义 IFAM 的 MCP 工具边界、输入输出、
科学约束和验收门槛。四工具 stdio 原型与独立 runner 已实现，契约和 tiny 黄金输出已通过
测试；真实 IFAM/HIBLUP 执行验收仍待 R/HIBLUP/PLINK 环境。它不代表已部署服务，也不允许
把其中的示例当作结果。

> 2026-10-18 校准：已核对用户下载的上游 `main.zip`
> （SHA-256 `b66f1a6d…91bd2b`，commit `62f8e4cd…f7649`）。输入发现规则、
> `anno_spec`、demo 表头和输出列名已据 `IFAM.R` 1.0.0 修正；R/HIBLUP/PLINK
> 仍未安装，执行级验证尚未完成。哈希与观察记录见
> [`UPSTREAM.md`](UPSTREAM.md)。

- 论文：Tang et al., *Nature Communications* (2026) 17:5686,
  [10.1038/s41467-026-72470-0](https://doi.org/10.1038/s41467-026-72470-0)
- 上游代码：[`xiaolei-lab/IFAM`](https://github.com/xiaolei-lab/IFAM)，
  commit [`62f8e4cd8ee53d70b3324ec5cd40d3f2ffbf7649`](https://github.com/xiaolei-lab/IFAM/commit/62f8e4cd8ee53d70b3324ec5cd40d3f2ffbf7649)
- 代码许可：仓库 `LICENSE` 与论文写 MIT；`Scripts/IFAM.R` 文件头写 GPL-3.0。
  **冲突未解决**，当前不 vendor、不再分发该脚本，只调用固定版本。HIBLUP 是
  独立外部依赖，使用与再分发前需单独核对许可。
- 论文包：[`../skill/ifam-paper`](../skill/ifam-paper)（reviewed_with_limitations）

## 1. 这个 MCP 要解决什么

IFAM 把多个功能注释分别当作随机效应，估计方差后把贡献相近（相差不超过 10 倍）
的注释合并，再用 HIBLUP 预测个体遗传值。真实入口是 `Scripts/IFAM.R`，它负责：

1. 读取 PLINK 二进制基因型、表型和注释 SNP 列表；
2. 为每个注释构建 GRM，估计方差组分；
3. 按 `randomMax` 和 10 倍规则合并随机效应；
4. 预测加性遗传值并写出 `.rand` 文件。

MCP 的价值不是重写 IFAM，而是把这条真实流水线包装成**可校验、可审计、可复用**的工具：
检查输入、提交作业、读取状态、导出结果。Cloudflare Pages 只做静态展示，不执行
R、HIBLUP、PLINK 或论文代码。

## 2. 上游事实（已核对）

以下内容来自对用户下载归档的只读检查：README、`Run_demo_Script.R`、
`Scripts/IFAM.R`、`demo_data.zip` 的表头与 `output.zip` 的实际输出。归档和
demo 数据在仓库外；哈希见 [`UPSTREAM.md`](UPSTREAM.md)。

### 2.1 运行环境

- Linux 或 macOS（上游明确推荐）。
- `IFAM.R` 1.0.0，`Rscript`，R 包 `optparse` v1.7.5。
- HIBLUP v1.1.0（外部可执行文件）。
- 首批不包装 `EA.R`、`GRMs_folder`、`weight` 或 `VCfile`。

### 2.2 真实参数

| IFAM.R 参数 | 默认值 | 契约中的含义 |
| --- | --- | --- |
| `--bfile` | 无 | PLINK 二进制前缀，不带 `.bed/.bim/.fam` |
| `--pheno` | 无 | 表型文件；第 1 列个体 ID，表型列由 `--pheno_pos` 指定 |
| `--pheno_pos` | `2` | 表型列号（1-based）；所选表头必须是安全文件名片段 |
| `--anno_folder` | 无 | 注释目录；其中**所有直接 `*.txt`** 都会被当作注释，不读取清单文件 |
| `--anno_spec` | `NULL` | 特殊注释 **stem（不带 `.txt`）**；不参与随机效应优化，仍作为随机效应计入模型。1.0.0 的多值路径有 bug，MVP 只支持 1 个 |
| `--randomMax` | `5` | 随机效应数量上限；特殊注释数量会从该上限中扣除 |
| `--VCmethod` | `AI` | `AI`、`EM`、`EMAI`、`HE`、`HI` |
| `--thread` | `1` | 线程数 |
| `--outPath` | 无 | 已存在目录，且必须以 `/` 结尾；wrapper 负责创建和规范化 |
| `--output_prefix` | `IFAM` | wrapper 固定为 `IFAM` |
| `--tmp_files` | `TRUE` | wrapper 固定传 `TRUE`，避免上游通配符清理；由 wrapper 管理保留 |
| `--GRMs_folder` | `NULL` | 预构建 GRM 目录；数量必须与**全部**注释数一致；首批不暴露 |
| `--weight` | `NULL` | SNP 权重文件；首批不暴露 |
| `--VCfile` | `NULL` | 预先估计的方差组分；首批不暴露 |

首批契约只暴露基础路径：`bfile`、`phenotype`、`phenotype_index`、
`annotation_dir`、`special_annotations`、`random_max`、`validation_split`、
`vc_method`、`threads`、`keep_intermediate`。`GRMs_folder`、`weight`、`VCfile`
先不暴露，因为还没有独立执行证据；后续作为扩展参数加入。

### 2.3 输入格式

- **基因型**：PLINK 1 二进制 `.bed/.bim/.fam`。不接受 VCF/HapMap/PED 直读；
  调用方先用 PLINK 转换。
- **表型**：首行有表头；第 1 列个体 ID；表型列可以是数值或 `NA`，列号由
  `phenotype_index` 指定。demo 的 ID 列名为 `Geno.id`，因此 ID 列名不是固定值。
  所选表型列会进入输出文件名，v1 要求它只含字母、数字、点、下划线或连字符。
- **注释**：`annotation_dir` 下每个直接 `*.txt` 文件都是一个注释；文件只有一列
  SNP ID，无表头。**不要放 `annotation_names.txt`**：上游脚本会把它也当作一个
  注释读取。上游 README 提到该清单，但代码没有这个机制。注释与基因型必须使用
  同一参考基因组版本；SNP ID 对不上时不要静默丢弃，inspect 会列为阻断项。
- **特殊注释**：`special_annotations` 使用不带 `.txt` 的注释 stem，例如
  `trait_snps`，传给 `--anno_spec trait_snps`。当有 `s` 个特殊注释时，上游用
  `randomMax - s` 作为剩余注释的优化上限，因此必须满足
  `random_max > s`，并把 `random_max - s` 作为 `effective_random_max`。
  **v1 只允许 `s = 1`**：1.0.0 的多值分支没有给 `anno_spec_file` 赋值，会失败；
  不要声称支持多个特殊注释。
- **路径字符**：上游把部分路径、注释名和表头拼进 shell 命令。所有路径与注释名
  必须是相对路径，且只含字母、数字、点、下划线、连字符和斜杠；拒绝空白、引号、
  分号、`$`、反引号、管道、重定向和 `..`。这是包装层的强制约束，不是上游保证。
- **缺失基因型**：PLINK 缺失编码 `01`，上游通过 HIBLUP 处理；契约记录缺失数量，
  不擅自填补。

### 2.4 上游实际输出

以 `outPath + output_prefix` 为前缀：

- `*.annotaion.information.txt`（上游拼写）：表头为
  `Annotations	Number_annotaions	Number_overlap_anno_map	Anno_cover_percent`；
- `*.overlaped.SNPs.between.anntations.txt`（上游拼写）：注释间 SNP 重叠矩阵；
- `*.<random-set>.txt`：合并后每个随机效应包含的 SNP 列表；
- `*_<trait>.rand`：个体 ID、每个随机效应的预测值、`genetic_values`（随机效应
  之和）、`residuals`；
- `*_<trait>.vars`：最终模型的方差组分，包含各随机效应和 `e`；
- `*_<trait>_vc.vars`：优化前的逐注释方差估计；上游随后删除 `_vc.beta` 和
  `_vc.rand`；
- HIBLUP 的 `.GA`、`.GA.bin`、`.GA.id`、`.log` 等中间文件，保留策略由 wrapper
  管理；
- 控制台日志，包含模型阶段和耗时。

`IFAM.R` 会打印并写出自己统计的注释数/覆盖率和重叠矩阵；wrapper 可用它们与
`ifam_inspect_inputs` 的独立计算做交叉核对。`IFAM.R` **不执行交叉验证，也不计算
Pearson、AUC 或预测偏差**。论文中的这些指标来自论文自己的训练/验证拆分和下游
评估。MCP 的 `ifam_export` 只负责把预测值和溯源信息规范化为可交接的记录；指标由
**独立的 benchmark runner** 在 MCP 边界之外，用 held-out truth 和记录下来的 split
计算。这样评测逻辑不会分散到各个方法的包装里。

### 2.5 论文与代码之间的版本差异

论文 Code availability 指向 Zenodo
[10.5281/zenodo.18802709](https://doi.org/10.5281/zenodo.18802709)，上游 README 的
citation 写的是 [10.5281/zenodo.18802710](https://doi.org/10.5281/zenodo.18802710)。
两者不能同时默认正确。实现时必须：

- 以 GitHub commit 为代码锚点；
- 分别解析两个 DOI 的元数据，记录差异；
- 在 provenance 中同时保留论文 DOI 与代码归档 DOI，不静默二选一。

### 2.6 许可冲突

仓库根目录的 `LICENSE` 是 MIT，论文 Code availability 也写 MIT；但
`Scripts/IFAM.R` 文件头声明 GPL-3.0。两者不能同时无条件成立。当前处理：

- 不把 `IFAM.R` 复制进本仓库、镜像或分发包，只在运行时调用用户提供的固定版本；
- 在 `tools.json` 的 `source.license_note` 与溯源记录中显式保留冲突；
- 在 vendor、重新分发或修改上游脚本之前，必须先完成许可核对；
- tiny fixture 与 Paper2Skill 包不包含上游脚本，不受该冲突影响。

## 3. 工具契约

机器可读版本见 [`tools.json`](tools.json)。通用约定：

- 所有路径都相对于服务端只读输入挂载根目录；拒绝绝对路径、`..` 和符号链接逃逸。
- 路径、注释名和所选表型表头必须通过字符白名单；上游 `system()` 调用使这一条
  成为硬约束，而不只是代码风格。
- 每次 fit 使用新的作业目录；不允许覆盖已有作业。
- 工具不执行任意 R 代码、不接收任意命令行参数、不访问外网。
- 响应中的路径是作业产物路径，不是公开 URL。
- `ifam_fit` 立即返回作业 ID；用 `ifam_job_status` 轮询；用 `ifam_export` 解析结果。

### 3.1 `ifam_inspect_inputs`（只读）

用途：在消耗计算资源前检查结构、ID 对齐、注释覆盖和潜在阻断项。

输入示例：

```json
{
  "input_root": "tiny",
  "bfile": "geno/tiny",
  "phenotype": "pheno/phenotype.fit.txt",
  "phenotype_index": 2,
  "annotation_dir": "annotations",
  "special_annotations": ["trait_snps"],
  "random_max": 5,
  "validation_split": "splits/repeat-1.json"
}
```

注释目录里没有 `annotation_names.txt`；四个 `.txt` 文件会被自动发现。
`validation_split` 用于预检：split 文件必须可解析，训练/验证 ID 不得相交，验证 ID
必须在 fit 表型中为 `NA`。**MCP 不接收 held-out truth**；truth 留在独立 benchmark
runner 一侧，避免拟合或导出工具接触评测标签。

必须返回：

- 个体数、SNP 数、注释数、优化/特殊注释数；
- phenotype 与 `.fam` 的 ID 对齐（缺失、多余、重复）；
- 每个注释的 SNP 数、去重后数目、覆盖率、未知 SNP；
- 注释两两交集和 Jaccard；
- 有效随机效应上限 `random_max - special_count`；
- 缺失基因型/单态 SNP 统计；
- `checks`、`blocking_errors`、`warnings`；
- 所有输入文件的 SHA-256。

阻断示例：PLINK 三件套缺失、重复个体 ID、表型列不是数值、注释目录没有 `.txt`、
注释文件为空或含表头、存在 `annotation_names.txt`、特殊注释 stem 不存在、给出
多个特殊注释、路径/名称含不安全字符、`random_max <= special_count`、
验证集 ID 在 fit 表型中仍有数值。

### 3.2 `ifam_fit`（异步提交）

用途：调用固定版本的 `IFAM.R` 完成 GRM、方差估计、合并和预测。

输入包含 `ifam_inspect_inputs` 的 `input_root`、`bfile`、`phenotype`、
`phenotype_index`、`annotation_dir`、`special_annotations`、`random_max` 和可选的
`validation_split`，外加：

```json
{
  "vc_method": "AI",
  "threads": 1,
  "keep_intermediate": false
}
```

`ifam_fit` **不接受** held-out truth；truth 始终留在独立 benchmark runner 一侧。
`validation_split` 在提交时用于阻断“验证集表型仍有数值”的拟合请求。首批
`special_annotations` 最多一个；多于一个在 JSON Schema 和运行时都要拒绝。

`keep_intermediate` 的服务端默认值是 `false`。wrapper **始终**给上游传
`--tmp_files TRUE`，避免 `IFAM.R` 执行 `rm <outPath><prefix>**`；作业结束解析完
主产物后，再由 wrapper 按该参数清理 HIBLUP 中间文件。主产物（`.rand`、注释信息、
重叠矩阵、`_vc.vars`、最终 `.vars`）始终保留。

返回：

```json
{
  "schema_version": "ifam.job.v1",
  "job_id": "ifam-20261018-3f2a9c1b",
  "state": "queued",
  "submitted_at": "2026-10-18T12:00:00Z",
  "effective_random_max": 4,
  "upstream": {
    "repository": "https://github.com/xiaolei-lab/IFAM",
    "commit": "62f8e4cd8ee53d70b3324ec5cd40d3f2ffbf7649",
    "entrypoint": "Scripts/IFAM.R",
    "hiblup": "1.1.0"
  },
  "command_fingerprint": "sha256:...",
  "warnings": []
}
```

实现要求：

- 外层以 `Rscript IFAM.R --flag value ...` 的 argv 数组调用，不拼接外层 shell 字符串；
- 上游内部会用 `system()` 拼 `hiblup`/`wc`/`rm` 命令，因此必须执行 §2.3 的路径
  与名称白名单，不能把任意用户路径直接传给脚本；
- `outPath` 由 wrapper 创建，规范化为以 `/` 结尾的作业目录；`output_prefix` 固定；
- 输入只读，输出目录按作业隔离；
- 不依赖上游退出码作为唯一成功信号：`q()` 默认退出 0，且 HIBLUP 失败可能被
  吞掉；必须检查 `.rand`、`.vars`、注释信息和重叠矩阵是否存在且可解析；
- 结束后确认 `*_<trait>.rand` 含 `ID`、各随机效应列、`genetic_values`、`residuals`；
- 记录上游命令、版本、输入哈希、随机效应合并结果和日志；
- 日志中不得出现外部凭据或未脱敏的受限数据路径；
- 不在本工具内计算 accuracy/AUC。

### 3.3 `ifam_job_status`（只读）

返回 `state` 与 `phase`：

```text
queued -> validating -> building_grms -> estimating_variance
       -> predicting -> parsing_outputs -> complete
```

任一阶段可进入 `failed`；用户可请求取消，进入 `cancelled`。`progress` 是从日志
解析的尽力而为信息，不能作为科学结果。错误必须带稳定 `code`、`message`、
`retryable` 和有限长度的 `log_tail`。

### 3.4 `ifam_export`（只导出预测，不计算指标）

用途：把 `*.rand`、注释信息和方差组分规范化为可交给独立 benchmark runner 的
predictions 记录。

- 只接受 `succeeded` 的作业；
- 输出 `sample_id`、`genetic_value`、可选 `residual`、方差组分、注释摘要、artifacts
  和 provenance；**不输出 Pearson r、AUC、prediction bias 或 evidence level**；
- 若 fit 时提供了 `validation_split`，导出必须确认预测覆盖全部验证 ID；缺任何一个
  即 `PREDICTIONS_INCOMPLETE`；
- 输出记录包含 `split_id`、`validation_ids` 和 `split_sha256`，供 runner 复核；
- 指标由独立 runner 计算：
  - `continuous`：验证集 Pearson r；
  - `binary`：验证集 AUC（0/1 truth，必须同时包含两类）；
  - prediction bias：以验证集表型为因变量、`genetic_values` 为自变量做线性回归，
    回归系数即论文定义的 bias，理想值为 1；
- 独立 runner 还必须拒绝以下泄漏：
  - fit 表型中验证 ID 不是 `NA`；
  - truth 文件中出现非验证 ID；
  - split 的训练集与验证集有交集；
  - 预测结果缺少验证 ID；
- 重复交叉验证（论文为 20 次，UKB 为 10 次）不在本 MVP 内；runner 先接受单次
  split 的 `exploratory` 记录，聚合、可比性和认证由后续 benchmark 流程负责。

## 4. 错误码

| code | 含义 | 可重试 |
| --- | --- | --- |
| `INPUT_NOT_FOUND` | 输入路径不存在或越界 | 否 |
| `PATH_NOT_ALLOWED` | 路径/名称含不安全字符、绝对路径、`..` 或符号链接逃逸 | 否 |
| `INVALID_PLINK_TRIO` | `.bed/.bim/.fam` 不完整或无法解析 | 否 |
| `DUPLICATE_INDIVIDUAL_ID` | ID 重复 | 否 |
| `ID_MISMATCH` | 表型与 `.fam` 不一致 | 否 |
| `PHENOTYPE_HEADER_INVALID` | 表头缺失，或所选列名不适合进入输出文件名 | 否 |
| `PHENOTYPE_NON_NUMERIC` | 目标列不是数值或 `NA` | 否 |
| `ANNOTATION_NOT_FOUND` | 注释目录没有 `.txt`，或指定文件缺失/为空 | 否 |
| `ANNOTATION_LAYOUT_INVALID` | 注释含表头/多列，或存在 `annotation_names.txt` 等会被误读的文件 | 否 |
| `UNKNOWN_ANNOTATION_SNP` | 注释 SNP 不在 `.bim` | 否（先修正输入） |
| `SPECIAL_ANNOTATION_INVALID` | 特殊注释 stem 不存在、含不安全字符，或给了多于一个 | 否 |
| `RANDOM_MAX_INVALID` | 上限不大于特殊注释数 | 否 |
| `RESOURCE_LIMIT` | 超出站点资源配额 | 可调整后重试 |
| `JOB_NOT_FOUND` | 作业 ID 未知 | 否 |
| `JOB_NOT_READY` | 作业未成功，暂不能导出 | 是 |
| `VALIDATION_SPLIT_INVALID` | split 不可解析、ID 缺失或训练/验证相交 | 否 |
| `VALIDATION_LEAKAGE` | 验证集表型在 fit 文件中仍有数值 | 否 |
| `PREDICTIONS_INCOMPLETE` | 导出预测未覆盖全部验证 ID | 否 |
| `INPUT_VALIDATION_FAILED` | inspect 有阻断项，fit 被拒绝 | 否 |
| `RUNTIME_UNAVAILABLE` | Rscript/HIBLUP/IFAM_ROOT 未就绪 | 安装后重试 |
| `UPSTREAM_HASH_MISMATCH` | `IFAM.R` 哈希与固定版本不符 | 否 |
| `PLINK_UNAVAILABLE` | 没有独立 PLINK 外部校验；不阻塞 Python subsetter 验收 | 安装后重试 |
| `UPSTREAM_FAILURE` | IFAM/HIBLUP 失败、退出码可疑或产物不完整 | 视错误而定 |

## 5. 科学边界与站点证据等级

- 本 MCP 的首批执行范围是合成夹具和公开 demo/小型公开子集；不接收 UKB、WTCCC
  或其他受限个体级数据。
- 不承诺复现论文全部表格。论文的 Duroc 数据为 2,796 头猪、约 1,134 万个 SNP，
  属于公开但大体量数据；必须先由用户下载并经独立校验，不能假设已存在。
- MCP 本身不产生证据等级；`ifam_export` 只交接预测。独立 runner 生成的单次 split
  记录先标为 `exploratory`，不进入站点排行。
- 只有经过人工复核、版本固定、数据许可确认的 benchmark 记录，才能作为站点 L1
  证据展示。论文报告的数值是 L3 参考，不与真实复现混排。
- 任何工具输出都必须携带论文 DOI、代码 commit、HIBLUP 版本和输入哈希。

## 6. 运行与安全

- MCP 不部署在 Cloudflare Workers/Pages 上；Pages 仅托管静态页面。
- 执行节点为隔离的 Linux worker，固定 R/HIBLUP 版本，默认无外网。
- 输入只读挂载；每作业独立输出目录；任务结束按保留策略清理。
- 命令参数白名单；路径规范化；拒绝 shell 注入和任意脚本。
- 上游脚本自身使用 `system()`，所以输入路径/注释名必须通过字符白名单；执行节点
  只允许固定哈希的 `IFAM.R`。
- 在许可冲突解决前，不把 `IFAM.R` 打进镜像或仓库；镜像只包含 wrapper 及依赖声明。
- CPU、内存、磁盘、墙钟时间配额由 worker 配置；超限返回 `RESOURCE_LIMIT`。
- 不把受限数据、个体级预测或未脱敏日志发布到静态站点。
- 公开产物必须保留上游归属、论文 CC BY 4.0 归属，并显式记录许可冲突。

## 7. 验收门槛（从 draft 到 certified）

1. **[已完成，许可除外]** 取得上游归档，记录 commit、关键脚本/demo ZIP 的
   SHA-256；确认 demo 表头、注释发现规则和输出列名。MIT 与 GPL 文件头的冲突
   仍待法律核对（见 §2.6）。
2. 在隔离环境安装 R、`optparse` v1.7.5、HIBLUP v1.1.0，独立运行上游 demo 的
   basic 和 advanced 流程，保存命令、日志、退出码和全部输出哈希。
3. 用独立 Python SNP-major subsetter 生成 500×5,000 子集，并用独立读取器验证
   `fixtures/tiny/geno/tiny.bed`；PLINK v1.90 可选，作为额外外部校验。
4. **[已完成本地实现]** 实现 FastMCP + R wrapper，只包装已验证参数；工具必须通过真实
   MCP stdio 调用；多特殊注释必须被 schema 与运行时同时拒绝。当前为纯 Python stdio
   原型（`server.py`），已通过 initialize、tools/list、inspect 黄金输出和 stub 管线测试；
   仍需在真实 demo 上验收。
5. 对每个工具做正例、反例和重复调用测试；`ifam_fit` 必须跑通夹具（或在
   HIBLUP 不支持的极小样本上明确记录限制）。必须验证 `NA` 表型个体的预测是否
   仍会输出，以确定验证集覆盖检查。
6. 把 wrapper 输出与上游直接执行结果逐列比较，至少覆盖 `.rand` 的
   `genetic_values`、注释覆盖和重叠矩阵。
7. 验证防泄漏：验证集表型有数值、split 训练/验证相交、预测缺少验证 ID 时都必须
   拒绝；truth 只在独立 runner 中读取，并测试其对齐与指标计算。
8. 记录资源上限、失败恢复、日志脱敏和清理策略；确认 wrapper 不触发上游
   `tmp_files = FALSE` 的通配符清理。
9. 通过独立 verifier 后，才允许把站点状态从“未认证”改为可调用；单次运行仍只能
   标记为 exploratory，不能直接进入排行。

## 8. 夹具

[`fixtures/tiny`](fixtures/tiny) 是 12 个合成个体、24 个 SNP、4 个注释（3 个优化 +
1 个特殊）的最小夹具。它故意包含：

- 4 个验证 ID 在 fit 表型中为 `NA`，truth 单独保存；MCP 不读取 truth，truth 只由
  独立 runner 使用；
- enhancer/promoter/tfbs 的重叠；
- 1 个 PLINK 缺失基因型；
- `trait_snps` 特殊注释（stem 为 `trait_snps`）及 `randomMax` 扣减；
- 注释目录中**没有** `annotation_names.txt`，只有四个可被上游自动发现的 `.txt`。

期望的 `ifam_inspect_inputs` 结果在
[`fixtures/tiny/expected/inspect_inputs.json`](fixtures/tiny/expected/inspect_inputs.json)。
夹具尚未经过 IFAM/HIBLUP 执行，不能作为科学结果或认证证据。

## 9. 未决事项

- HIBLUP v1.1.0 暂不可得：官网当前只列出 v1.7.0，历史条目的 v1.1.0 没有下载链接。
  真实执行验收暂时挂起；不能用 v1.7.0 静默替代。
- 已用 **真实 IFAM.R + fake HIBLUP** 跑通 MCP dry-run；它验证参数、作业、导出和
  runner 管线，但数值不是 IFAM/HIBLUP 证据。
- 本地 stdio 原型已实现 inspect/fit/status/export 和独立 runner；fit 只用 fake
  engine 验证过作业管理/导出管线，尚未跑真实 IFAM。
- R 4.6.1 + optparse 1.8.2 已安装；上游 README 固定 optparse 1.7.5，真实验收时需
  在 provenance 记录版本差异。
- `IFAM.R` 的 MIT/GPL 许可冲突待法律核对；在此之前不 vendor、不再分发。
- 上游 1.0.0 的多特殊注释路径有 bug；首批只支持一个，待上游修复后再评估。
- HIBLUP 对 `NA` 表型个体是否逐个体输出预测尚未实测。
- Zenodo 18802709/18802710 的差异待解析。
- 上游 README 的 `annotation_names.txt` 说法与代码不一致；本契约以代码为准。
- `GRMs_folder`、`weight`、`VCfile`、EA 流程暂不暴露，待单独验证。
- 多拆分交叉验证、聚合和站点认证流程尚未实现。

归档保存在仓库外（用户下载目录）；本仓库只记录核对结果、哈希和许可说明，不提交
上游压缩包、demo 数据或输出。


# SBayesRC MCP 工具契约（草案）

状态：**draft / 本地 stdio 实现 / 未认证**。本文件定义 SBayesRC MCP 的工具边界、
输入输出、科学约束和验收门槛。六个工具的 stdio 服务已实现，并已在一套自带的
确定性玩具数据（60 样本 × 18 SNP × 3 LD block）上通过 pytest 与独立验收。

> 本地实测环境：R 4.4.3 + SBayesRC 0.2.6（commit `2881f9a6…`）+ plink2
> （静态二进制）。SBayesRC 的数值执行验收已完成于玩具数据；论文级（UKB ~7M SNP）
> 执行**未**发生，不在本包承诺范围内。

- 论文：Zheng et al., *Nature Genetics* (2024) 56:1211–1222,
  [10.1038/s41588-024-01704-y](https://doi.org/10.1038/s41588-024-01704-y)
- 上游代码：[`zhilizheng/SBayesRC`](https://github.com/zhilizheng/SBayesRC)，
  commit [`2881f9a6f57374b80b4d19a09dbf9387939a2f46`](https://github.com/zhilizheng/SBayesRC/commit/2881f9a6f57374b80b4d19a09dbf9387939a2f46)，版本 0.2.6
- 合并源码（R 包 + GCTB）：[10.5281/zenodo.10416921](https://doi.org/10.5281/zenodo.10416921)
- 代码许可：**GPL-3.0**。本包**不 vendor、不再分发**上游源码，只固定 commit 并在
  运行时通过 `Rscript` 调用已导出的 R 函数。原生 LD 生成引擎 GCTB
  （[`jianzeng/GCTB`](https://github.com/jianzeng/GCTB)，同为 GPL-3.0）也不在本包内。
- 论文包：[`../skill/sbayesrc-paper`](../skill/sbayesrc-paper)（reviewed_with_limitations）

## 1. 这个 MCP 要解决什么

SBayesRC 是**基于 GWAS summary statistics** 的贝叶斯多基因评分（PGS）方法：把
GWAS 汇总统计与 LD 相关矩阵、功能注释结合，估计 SNP 联合效应并给出多基因预测。
它只要求 summary + LD 参考，不需要个体基因型（相对于 GSGP-Bench 中走个体基因型的
GBLUP/IFAM 路线，这是另一条输入模态）。

真实入口是 R 包的导出函数。MCP 的价值不是重写 SBayesRC，而是把这条流水线包装成
**可校验、可复用**的工具：QC 汇总 → 插补缺失 → 拟合模型 → 计算 PRS → 跨祖先组合
→ LD 消融。科学计算全部在原始 R 包内执行，Python 只实现 JSON 契约与 `Rscript`
转发。

## 2. 上游事实（已核对）

### 2.1 运行环境

- Linux（x86-64）或 macOS；本包实测于 Linux。
- R 4.4.3 + SBayesRC 0.2.6（固定 commit）。SBayesRC 从源码构建，`BH` 必须固定为
  1.84.0（包使用 `CXX_STD=CXX11`，更新的 BH 会破坏构建）。
- `plink2` 静态二进制：仅 `sbayesrc_prs` 需要。
- Python 3.12 + FastMCP 4.0.3 + mcp（见 `src/requirements.txt`）。

### 2.2 真实工具与上游绑定

| MCP 工具 | 上游 R 函数 | 说明 |
| --- | --- | --- |
| `sbayesrc_tidy_summary` | `SBayesRC::tidy` | 等位基因/频率/样本量/var-2pq QC |
| `sbayesrc_impute_summary` | `SBayesRC::impute` | 从 LD 参考插补缺失汇总 |
| `sbayesrc_sbayesrc_run` | `SBayesRC::sbayesrc` | 贝叶斯混合模型；权重/遗传力/富集 |
| `sbayesrc_prs` | `SBayesRC::prs` | 经 `plink2` 计算 PRS |
| `sbayesrc_sbrc_multi` | `SBayesRC::sbrcMulti` | 两个祖先 PRS 的表型加权组合 |
| `sbayesrc_cut_ld` | `SBayesRC::cutLD` | 降低 LD 参考特征值阈值 |

首批**不暴露** `LDstep1–4`（LD 生成），因其需要外部 GCTB 二进制；也不暴露
`SBayesRC::adjLD` 等未在本包验收的入口。

### 2.3 输入 / 输出格式

- **GWAS 汇总**：COJO 格式 `SNP A1 A2 freq b se p N`（tab 分隔，带表头）。
- **LD 参考**：SBayesRC LD 参考文件夹，含 `snp.info`、`ldm.info`、`block*.eigen.bin`、
  `b*.ldm.full.{info,bin}`。由 `LDstep1–4` + GCTB 生成，或从资源站下载预构建 LD。
- **注释**（可选）：SNP + 注释列的表文件（如 BaselineLD 2.2）。
- **PRS 输出**：`<outPrefix>.score.txt`，列 `FID IID ALLELE_CT SCORE`。
- **模型输出**：`<outPrefix>.txt`（权重）、`.par`（遗传力/结构参数）、
  `.AnnoPerSnpHsqEnrichment`、`.AnnoJointProb`、`.rds`。

统一返回：`{tool, outputs, summary, artifacts:[{path,exists}], message, reference}`。

### 2.4 上游实际输出与已知问题

- **`sbayesrc_run` 非逐位可复现**：上游 `src/dist.cpp` 从无种子的
  `thread_local std::mt19937_64` 取样；`seed` 参数被接受但不种那个 RNG。相同输入
  两次运行 hsq 可差到约 2.2–2.9。可复现的是结构性属性（SNP 集合/顺序、产物
  schema、PIP 范围），不是精确数值。
- **LD 生成需要 GCTB**：`LDstep1–4` 依赖外部 `gctb` 二进制（`--make-full-ldm`），
  本包不提供。复现论文主结论用**预构建 LD**即可，不必自建。
- **参考资源为多 GB 外链**：BaselineLD 注释、~7M SNP 的 LD 矩阵托管在
  `gctbhub.cloud.edu.au`，不随包分发。
- **平台**：仅 Linux x86-64 实测。

### 2.5 许可

SBayesRC 为 GPL-3.0；GCTB 同为 GPL-3.0。**不复制、不修改、不再分发**上游源码，
只在运行时调用固定版本。本目录内的 `src/` 是本项目的 Python 包装层（非上游代码），
`renv.lock` 是版本锁定清单（非源码）。

## 3. 工具契约

六个工具的机器可读 schema 见 [`tools.json`](tools.json)。逐个说明如下。

### 3.1 `sbayesrc_tidy_summary`（QC）

- 输入：`mafile`、`ld_dir`、`output`，可选 `freq_thresh`、`N_sd_range`、`rate2pq`。
- 输出：整理后的 `output` + `.full` + `.log`；`summary.n_variants_out`。
- 只读输入；幂等。

### 3.2 `sbayesrc_impute_summary`（插补）

- 输入：`mafile`、`ld_dir`、`output`，可选 `thresh`。
- 输出：覆盖全部 LD SNP 的 `.ma`；`summary.n_variants`、`summary.n_imputed`
  （`r2==0` 计数）。幂等。

### 3.3 `sbayesrc_sbayesrc_run`（拟合）

- 输入：`mafile`、`ld_dir`、`out_prefix`，可选 `annot` 及 MCMC 旋钮
  （`niter/burn/tune_iter/tune_burn/seed/out_freq`）。
- 输出：权重 `.txt`、参数 `.par`、富集 `.AnnoPerSnpHsqEnrichment`、`.AnnoJointProb`、
  `.rds`；`summary.n_snps/hsq_mean/nnz_mean`。
- **非幂等**（见 2.4）；**明确不计算 held-out 指标**。

### 3.4 `sbayesrc_prs`（PRS）

- 输入：`weight`、`geno_prefix`、`out_prefix`，可选 `geno_chr/snplist/keepid/plink2`。
- 输出：`<out_prefix>.score.txt`；`summary.n_samples/n_alleles`。
- 通过 `plink2` 执行；**不计算指标**。

### 3.5 `sbayesrc_sbrc_multi`（跨祖先）

- 输入：`prs1`、`prs2`、`out_prefix`、`tuneid`、`pheno`，可选 `keepid`。
- 输出：加权分数 `<out_prefix>.score.txt` + 组合权重 `.weight`。幂等。

### 3.6 `sbayesrc_cut_ld`（LD 消融）

- 输入：`input_ld`、`output_ld`、可选 `thresh`。
- 输出：降维 LD 参考目录。**不计算指标**。

## 4. 错误码

工具层不返回结构化错误码；失败表现为 MCP 工具错误，消息来自 R 侧
（`status != "ok"` 时抛出，附 R stderr 末若干行）。常见失败：

| 触发 | 表现 |
| --- | --- |
| 输入文件/目录不存在 | MCP 工具错误 `file not found: <path>` |
| R 调用返回非零 | MCP 工具错误 `R tool '<tool>' failed (rc=...)` + stderr 尾部 |
| R 返回非 JSON | MCP 工具错误 `... returned non-JSON on stdout` |
| 环境缺 Rscript/plink2 | 同上，源自 R 侧或子进程 |

## 5. 科学边界与站点证据等级

- 本 MCP **不接收 held-out truth**，**不在 MCP 内计算任何 benchmark 指标**。
  预测/权重由工具产出，指标由仓库外的独立 runner 计算。
- 玩具数据上的通过只代表**工程验收**，不是科学结论，也不能进入排行榜。
- 论文报告的 14%（欧洲人群）/ 34%（跨祖先）提升是**论文报告值**，本包不声称已复现。

## 6. 运行与安全

- stdio 传输。服务器读取的运行时路径来自 **MCP stdio 启动配置的环境变量**
  （`P2A_RSCRIPT`、`P2A_R_PROJECT`、`P2A_PLINK2`），不来自客户端进程。
- 不执行任意用户代码；工具路径直接传给上游 R 函数（不做沙箱），调用方应保持路径
  不含 shell 元字符。
- 凭据不进入源码、报告或产物。

## 7. 验收门槛（从 draft 到 certified）

中央团队在固定版本 + 参考数据上检查：

1. 有来源：DOI、仓库、commit、许可证 —— 见 `tools.json.source`；
2. 有 MCP 契约：工具/输入/输出/版本 —— `tools.json`；
3. 能启动：stdio 说明清楚（见 `README.md`）；
4. 能跑参考数据：`fixtures/tiny` 上可复现的调用；
5. 能产出预测/结果文件，字段符合约定；
6. 不接收 held-out truth、不在 MCP 内算指标；
7. 与直接运行/参考实现对比在容差内（确定性工具逐位，`sbayesrc_run` 比结构性属性）；
8. 不执行任意用户代码；
9. 有清晰限制、失败模式、联系方式。

任一项不满足 = 未认证。

## 8. 夹具

`fixtures/tiny/`：60 样本 × 18 SNP × 3 LD block 的确定性玩具数据。
`summary/toy.ma`（COJO 汇总）、`ld/`（LD 参考）、`annotations/toy_annot.txt`、
`geno/toy_bfile.{bed,bim,fam}`、`pheno/toy_pheno.txt`、`pheno/toy_tune.id`。
生成脚本 `gen_toy.R` / `build_toy_ld.R` 随附以保留溯源；`run_reference.R` 是直接
调用 R 包的独立参考路径。

## 9. 未决事项

1. **GCTB 集成**：是否扩展暴露 `LDstep1–4`，将取决于是否把 GCTB 一起纳入（编译
   产物 + GPL 合规）。当前不纳入。
2. **论文级复现**：需要 UKB（申请 12505）+ BaselineLD 2.2 + ~7M SNP LD 参考 +
   GCTB（如需自建 LD）。属于后续阶段。
3. **跨祖先数据**：FinnGen R8 / BBJ / PAGE 需分别申请。
4. **`sbayesrc_run` 可复现性**：上游 RNG 问题未解决；若需可复现数值，需上游改动，
   不在本包控制内。

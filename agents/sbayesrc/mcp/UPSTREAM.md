# SBayesRC 上游核对记录

> 快照：2026-10-29。上游源码由本项目在固定 commit 从 GitHub 取得并在运行时调用；
> 本仓库**不包含**上游 R 包源码、GCTB 源码或任何参考数据。以下哈希用于溯源。

## 1. 代码锚点

| 项 | 值 |
| --- | --- |
| 上游仓库 | `https://github.com/zhilizheng/SBayesRC` |
| 固定 commit | `2881f9a6f57374b80b4d19a09dbf9387939a2f46` |
| 版本 | `0.2.6`（`DESCRIPTION`）|
| 发布 tarball | `.../releases/download/v0.2.6/SBayesRC_0.2.6.tar.gz` |
| 合并源码（R 包 + GCTB） | Zenodo `10.5281/zenodo.10416921` |
| 许可 | **GPL-3.0**（仓库根 `LICENSE` 与 `LICENSE.md`）|
| 处理方式 | 从固定 commit 构建到隔离 renv 库；运行时 `Rscript` 调用导出函数。未 vendor、未再分发。 |

## 2. 本目录内本项目自有文件的哈希（非上游源码）

| 文件 | SHA-256 |
| --- | --- |
| `src/sbayesrc_mcp.py` | `d79ac47f7022009daa823f7f6eab1735b2ae166eeb296e10102efb5bc9c4ec85` |
| `src/tools/sbayesrc.py` | `14e8bac070cd3ec2b08f701f387647daa8ac85fd28d0a540eaceb425dc1f7254` |
| `src/r_scripts/sbayesrc.R` | `af889e9f93c18c181551f9cf5362378c1dd8e776e4a33b6018bf10192899364c` |
| `renv.lock` | `fd4aefb9f594b01574eeef6d8f7a829645cd4a1f2d1bec0187bad6b0eaf4a505` |
| `tools.json` | `53849031f32f9a12b1fe5a7fbe6f6b4ee4b5dce3a67de198fe6df9b22812228f` |

## 3. 夹具哈希（合成数据，可自由分发）

| 文件 | SHA-256 |
| --- | --- |
| `fixtures/tiny/summary/toy.ma` | `84eac8f625345b750eeb4e05dffeae65eecdd6de31ed5f1763eaeaaea27bb140` |
| `fixtures/tiny/geno/toy_bfile.bed` | `9b46c6c0a9cdb1e1e64bf33b3f76c07f954aba55f43fe6e861029fc52c6efe84` |

夹具为 60 样本 × 18 SNP × 3 LD block 的确定性合成数据，由随附的 `gen_toy.R` /
`build_toy_ld.R` 生成，无真实个体数据。

## 4. 已核对的事实

### 4.1 环境

- R 4.4.3 + SBayesRC 0.2.6；从源码构建，`BH` 必须固定 **1.84.0**
  （包 `Makevars` 使用 `CXX_STD=CXX11`，更新 BH 破坏构建）。
- `plink2` 静态二进制仅 `prs` 需要。
- Python 3.12 + FastMCP 4.0.3。

### 4.2 工具绑定

`sbayesrc_tidy_summary→tidy`、`impute_summary→impute`、`sbayesrc_run→sbayesrc`、
`prs→prs`（`system()` 调 `plink2`）、`sbrc_multi→sbrcMulti`、`cut_ld→cutLD`。
均为 SBayesRC 的导出函数（`NAMESPACE` 确认）。

### 4.3 上游问题（保留，不隐藏）

1. **许可**：SBayesRC 与 GCTB 均为 GPL-3.0。本包不 vendor、不再分发；只固定 commit
   在运行时调用。
2. **`sbayesrc_run` 非逐位可复现**：`src/dist.cpp` 用无种子的
   `thread_local std::mt19937_64`；`seed` 不种该 RNG。相同输入 hsq 可差到约 2.2–2.9。
3. **LD 生成需 GCTB**：`LDstep1–4` 依赖外部 `gctb`（`--make-full-ldm`）；本包不
   提供，也不暴露这四个函数。复现论文主结论用预构建 LD 即可。
4. **参考资源外链**：BaselineLD 2.2 注释、~7M SNP LD 矩阵托管在
   `gctbhub.cloud.edu.au`（实测可达；HapMap3 EUR LD `ukbEUR_HM3.zip` 约 3.1 GB）。
5. **平台**：仅 Linux x86-64 实测。

## 5. 仍未完成

- 论文级（UKB ~7M SNP）复现：需 UKB（申请 12505）+ BaselineLD 2.2 + LD 参考，
  外加算力排期；不在本包承诺范围内。
- 跨祖先数据（FinnGen R8 / BBJ / PAGE）分别需申请。
- 如需自建 LD：需编译 `jianzeng/GCTB`（源码含 `scr/Makefile`，依赖 Eigen3 + Boost）
  并考虑是否扩展暴露 `LDstep1–4`（涉及 GPL 合规）。

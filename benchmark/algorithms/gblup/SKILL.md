# GBLUP baseline Skill（manual baseline）

> 这是一个**自建基线**，不是 Paper2Agent 从论文自动生成的 Skill，也不是认证 MCP。
> 它的作用是给 GSGP-Bench 提供可复现的对照方法，并验证证据链路。

## 论文来源

VanRaden, P. M. **Efficient methods to compute genomic predictions.**
*Journal of Dairy Science* 91:4414–4423 (2008).
DOI: [10.3168/jds.2007-0980](https://doi.org/10.3168/jds.2007-0980)

## 方法

GBLUP 使用一个基因组关系矩阵（GRM）和一个随机遗传效应：

- 基因型：PLINK 1 `.bed/.bim/.fam`；
- GRM：VanRaden method 1，`G = ZZ' / (2 Σ p(1-p))`；
- 方差组分：单随机效应 REML；
- 预测：用训练个体表型和验证个体基因型预测验证集遗传值；
- 不执行交叉验证，不计算 Pearson/AUC/bias；
- 指标由 MCP 之外的独立 runner 使用 held-out truth 计算。

## 输入

- `bfile`：PLINK 二进制前缀；
- `phenotype`：第 1 列个体 ID，目标列可为数值或 `NA`；
- `phenotype_index`：目标列号；
- `validation_split`：可选 split JSON，验证 ID 在 fit 表型中必须为 `NA`。

## MCP 工具

本地 stdio 原型（manual baseline）：

1. `gblup_inspect_inputs`：检查 PLINK、表型、ID 对齐和 split；
2. `gblup_fit`：拟合 GBLUP/REML，返回验证集预测和 provenance；
3. `gblup_export`：读取已完成的 run。

MCP 不接收 truth，不输出指标。服务代码在
[`server.py`](server.py)，契约在 [`tools.json`](tools.json)。

## 输出

`gblup_fit`/`gblup_export` 返回：

- `run_id`；
- `predictions`：`sample_id`, `genetic_value`；
- `validation_ids`；
- `fit`：lambda、方差组分、样本/SNP 数；
- `provenance`：论文 DOI、输入哈希、代码哈希、环境。

公开结果遵循 [`benchmark/schema/result.v1.json`](../../schema/result.v1.json)；
当前例子是 [`gblup-sim500-mcp-v1`](../../runs/gblup-sim500-mcp-v1/result.json)，
证据等级 **EXP**。

## 运行

```bash
python3 benchmark/run_gblup_mcp_trial.py \
  --run-id gblup-sim500-mcp-v1
```

## 局限

- 只手写了一个基线，不代表 Paper2Agent 的生成能力；
- 单随机效应，不支持 IFAM 的多注释随机效应；
- 当前数据是 500×5k 上游 demo 子集 + 模拟性状，不是论文 Duroc 表型；
- 单次划分，不是 L1；
- 不能在静态网页内执行，网页只展示证据记录。

# 端到端示例：从论文来源到 EXP 结果

> 这条示例的目标不是“证明 GBLUP 比别的算法好”，而是把
> **论文来源 → 数据/划分 → 真实预测 → 独立 runner → 证据记录 → 前端**
> 这条链完整走一遍，并明确它还不是 L1。

## 1. 论文来源

GBLUP 基线使用：

> VanRaden, P. M. **Efficient methods to compute genomic predictions.**
> *Journal of Dairy Science* 91:4414–4423 (2008).
> DOI: [10.3168/jds.2007-0980](https://doi.org/10.3168/jds.2007-0980)

这不是 IFAM 论文。IFAM 的 Paper2Skill/MCP 试点使用：

> Tang et al. **Improving genomic prediction accuracy of complex traits by
> integrating massive types of functional annotation information.**
> *Nature Communications* 17:5686 (2026).
> DOI: [10.1038/s41467-026-72470-0](https://doi.org/10.1038/s41467-026-72470-0)

## 2. 数据来源

本次 GBLUP 示例的数据是：

- 基因型：上游 IFAM demo 的 **500 个体 × 5,000 SNP** 子集；
- 本地路径：`local_data/ifam-demo-500x5k/`（gitignored，不提交）；
- 性状：**由 GSGP-Bench 模拟**，h² = 0.5，200 个因果 SNP，seed `20261019`；
- 划分：一次 80/20，400 训练 / 100 验证；
- 原始基因型、表型和个体预测不发布，公开记录只保留聚合指标和哈希。

因此，这个例子的科学含义是“在已知模拟性状上验证流程”，不是 IFAM 论文的
Duroc 表型，也不是任何论文表格的复现。

## 3. 真实运行

```bash
# 如果本地还没有 500×5k 子集
python3 benchmark/prepare_demo_subset.py \
  --ifam-root "$HOME/Downloads/IFAM-main"

# 生成模拟性状、拟合 GBLUP、独立评测、写证据
python3 benchmark/run_gblup_sim.py \
  --source-subset local_data/ifam-demo-500x5k \
  --run-id gblup-sim500-v1
```

运行会先生成一条 direct control，再通过 GBLUP baseline MCP 产生站点使用的记录：

```bash
python3 benchmark/run_gblup_mcp_trial.py --run-id gblup-sim500-mcp-v1
```

MCP 记录得到：

| 指标 | 值 |
| --- | --- |
| Pearson r | 0.5075 |
| R² | 0.2576 |
| prediction bias slope | 1.2117 |
| 运行时 | < 0.1 分钟 |
| 证据等级 | **EXP / exploratory** |

拟合代码不读取 truth；`agents/ifam/mcp/runner.py` 在外部读取 held-out truth 并计算指标。

## 4. 证据记录

- MCP 公开记录：[`benchmark/runs/gblup-sim500-mcp-v1/result.json`](../benchmark/runs/gblup-sim500-mcp-v1/result.json)
- MCP runner 输出：[`benchmark/runs/gblup-sim500-mcp-v1/metrics.json`](../benchmark/runs/gblup-sim500-mcp-v1/metrics.json)
- Direct control：[`benchmark/runs/gblup-sim500-v1/result.json`](../benchmark/runs/gblup-sim500-v1/result.json)
- 站点副本：[`site/data/results/gblup-sim500.json`](../site/data/results/gblup-sim500.json)
- 记录 schema：[`benchmark/schema/result.v1.json`](../benchmark/schema/result.v1.json)
- 证据规范：[`docs/证据等级与记录.md`](证据等级与记录.md)

记录中明确包含：

- `algorithm.paper_doi` / `algorithm.paper_title`（论文来源）；
- `dataset.source`（上游 demo 基因型 + 模拟性状、seed、h²）；
- split、输入哈希、预测哈希、runner 哈希；
- `evidence.level = exploratory`、`single_split = true`、`certified = false`；
- `mcp` 字段记录 `gblup_inspect_inputs → gblup_fit → gblup_export` 的 stdio 调用。

## 5. 前端如何显示

站点中新增数据集 **GSGP-Sim 500×5k**，GBLUP 单元格显示：

```text
0.508
EXP · 探索
```

- **EXP** 用点状柱，区别于 L1 实心、L3 斜线；
- 证据计数显示 `1 EXP`；
- 详情抽屉显示论文来源、数据来源、run ID、划分、实现和证据账本路径；
- 页面横幅写明 `DEMO DATA + 1 EXP RUN`，其余数字仍是演示值。

## 6. 和 Paper2Agent 链路的关系

现在有两条真实链路：

```text
A. GBLUP 单方法全链（manual baseline）
   VanRaden 2008
     → 自建 GBLUP SKILL
     → 本地 GBLUP MCP（inspect/fit/export）
     → MCP 预测
     → 独立 runner
     → result.v1 + 证据账本
     → 站点 EXP

B. Paper2Agent 生成/验证（IFAM）
   IFAM 论文
     → Paper2Skill（reviewed_with_limitations）
     → MCP stdio 四工具
     → 真实 IFAM.R + fake HIBLUP 的 dry-run
     → STUB 结果填充 sim500（仅管线展示）
     → 仍未做真实 HIBLUP 数值
```

GBLUP 这条已构成**单方法完整闭环**，但 Skill/MCP 是**手动 baseline**，不是
Paper2Agent 生成物；它证明平台能闭环，不证明生成能力。IFAM 这条是
Paper2Agent/STUB lane：Skill/MCP 流程真实，数值由 fake HIBLUP 填充，不能当科学结果。

## 7. 这条示例证明了什么

- 论文来源可以进入结果记录，而不是只在 UI 上放一个 DOI；
- 数据来源、模拟参数、划分和哈希可以进入证据账本；
- 真实预测由独立 runner 评分，MCP/拟合代码不接触 truth；
- 前端能消费结果 JSON，并把 EXP 与 demo/L1/L3 分开；
- 结果可以在不提交原始数据的情况下公开聚合指标和溯源。

它没有证明：Paper2Agent 自动生成 GBLUP 的能力、IFAM 真实数值、L1 复现、跨方法排名或论文结论。

## 8. 下一步

1. 保持本条记录为 **EXP**，不要升级为 L1。
2. 如果要做 L1，先固定多折/多 seed 协议、审核流程和完整 run manifest。
3. 如果要让**同一篇论文**走完 Skill → MCP → bench，最简单的下一步是给 GBLUP
   增加一个正式的 Paper2Skill/MCP（但那是我们自己的基线包装，不是 Paper2Agent
   从论文自动生成的产物），或等待 HIBLUP v1.1.0 后完成 IFAM 实跑。

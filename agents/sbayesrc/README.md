# SBayesRC 垂直切片

本目录是 GSGP-Bench 的第二个论文试点，覆盖 SBayesRC。它把“读懂论文”和“运行方法”
拆成两个独立交付物，并明确标注哪些已经完成、哪些只是草案。

> 状态快照：2026-10-29。已有本地 MCP stdio 实现（6 工具）与已审校的 Paper2Skill
> 包；玩具数据上的工程验收通过。**没有**论文级（UKB ~7M SNP）复现结果，也没有
> 部署服务。评测数值、认证徽章和排行榜仍属于后续阶段。

## 论文、SBayesRC 与 GCTB 的关系

这三者不是同一个东西：

| 层 | 是什么 | 在本项目中的角色 |
| --- | --- | --- |
| SBayesRC 论文 | Zheng et al., *Nature Genetics* 2024, 56:1211–1222 | 定义方法：基于 summary statistics 的贝叶斯 PGS，整合功能注释与全基因组变异；也是 Paper2Skill 的来源 |
| SBayesRC 代码 | `zhilizheng/SBayesRC` R 包 0.2.6 | 论文方法的 R 实现：QC、插补、贝叶斯混合模型、PRS、跨祖先组合、LD 消融；也是 MCP 的运行后端 |
| GCTB | 独立基因组软件（外部依赖，`jianzeng/GCTB`） | 原生引擎：SBayesRC 的 R 包通过它生成 LD 参考（`LDstep1–4` → `gctb --make-full-ldm`）；**不是**本试点必需 |

所以：

- 论文的**方法与主结论**由 R 包实现；本 MCP 包的就是它。
- **生成自建 LD** 需要 GCTB（外部二进制，GPL-3.0，本包不含）；但复现论文主结论
  用**预构建 LD** 即可，不必自建。
- 与 IFAM 路线（个体基因型 + 多组学注释）不同，SBayesRC 走 **GWAS summary +
  LD 参考 + 功能注释**，是另一条输入模态。

## 目录

| 路径 | 内容 | 状态 |
| --- | --- | --- |
| `skill/sbayesrc-paper/` | 已审校的 Paper2Skill 包：3 个文档 + 26 主图 + 2 主表 + 115 补充图 + 11 补充表 | `reviewed_with_limitations` |
| `mcp/CONTRACT.md` | SBayesRC MCP 的工具边界、科学约束、错误码、验收门槛 | draft |
| `mcp/tools.json` | 6 个工具的机器可读 schema | draft |
| `mcp/src/sbayesrc_mcp.py` | FastMCP stdio 服务入口 | 已实现，未认证 |
| `mcp/src/tools/sbayesrc.py` | 工具的 JSON 契约与 `Rscript` 转发 | 已实现 |
| `mcp/src/r_scripts/sbayesrc.R` | R 侧分发器（加载 renv 并调用导出函数）| 已实现 |
| `mcp/renv.lock` | R 库版本锁定清单（restore 目标，不含源码）| 已生成 |
| `mcp/README.md` | MCP 的文件清单、当前已验证项、运行方式 | — |
| `mcp/UPSTREAM.md` | 上游 commit、哈希、格式核对记录 | 已核对 |
| `mcp/USAGE.md` | 面向使用者的安装/配置/工作流说明（包相对路径）| — |
| `mcp/fixtures/tiny/` | 60×18×3 合成夹具及期望检查 | 工程验收通过 |

本目录**不 vendor** 上游 GPL-3.0 源码（SBayesRC / GCTB），只固定 commit 在运行时调用。
站点副本（如生成）不得作为源文件；修改应发生在本目录，再重新生成预览。

## Paper2Skill 的证据

最终构建与严格验证结果：

- 总体状态：`reviewed_with_limitations`；
- `mechanical_ok: true`，`issues: []`；
- 111 页全部人工审校，`all_sources_agent_reviewed: true`；
- 25 项来源裁定已应用，0 项 stale；
- `paper_bundle.py verify --strict` 退出码 0。

## Paper2MCP 的证据

- 6 个工具全部暴露；玩具数据上 8 个验收用例在**两套解释器**下通过；
- 确定性工具与直接调用 R 包的独立参考一致；`sbayesrc_run` 比结构性属性一致；
- 交付 ZIP 在异目录 + 含空格路径下解压重建并真实调用通过；
- **未**在 UKB 等真实大数据上运行。

## 未决事项

1. 论文级复现需 UKB（申请 12505）+ BaselineLD 2.2 + ~7M SNP LD 参考 + 算力。
2. 是否需要纳入 GCTB（编译产物 + GPL 合规）以支持自建 LD。
3. 许可：SBayesRC/GCTB 均 GPL-3.0，本仓库 MIT，故不 vendor，仅固定 commit 调用。

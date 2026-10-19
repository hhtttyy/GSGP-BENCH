# IFAM 垂直切片

本目录是 GSGP-Bench 的第一个论文试点，只覆盖 IFAM。它把“读懂论文”和“运行方法”
拆成两个独立交付物，并明确标注哪些已经完成、哪些只是草案。

> 状态快照：2026-10-18。已有本地 MCP stdio 原型、独立 runner 和契约测试；没有部署
> 服务，也没有 IFAM 的基准复现结果。真实 IFAM/HIBLUP 执行验收等待 R/HIBLUP。
> 评测数值、认证徽章和排行榜仍属于后续阶段。

## 论文、IFAM 与 HIBLUP 的关系

这三者不是同一个东西：

| 层 | 是什么 | 在本项目中的角色 |
| --- | --- | --- |
| IFAM 论文 | Tang et al., *Nature Communications* 2026 | 定义方法：多注释随机效应、10 倍方差合并、数据与评测设置；也是 Paper2Skill 的来源 |
| IFAM 代码 | `IFAM-main/Scripts/IFAM.R` 1.0.0 | 论文方法的 R 编排层：发现注释、构造 SNP 列表、调用外部引擎、合并随机效应、解析并重写 `.rand` |
| HIBLUP | 独立基因组 BLUP 软件（外部依赖） | 数值引擎：构建 GRM、估计方差组分、拟合多随机效应并预测遗传值；IFAM.R 通过 `system()` 调用 |

IFAM.R 本身不实现 BLUP/REML。它把工作交给 `hiblup` 的三个调用：

```text
hiblup --make-xrm       → 每个注释/随机效应组的 GRM
hiblup --single-trait   → 方差组分（--vc-method AI/HE/...）
hiblup --single-trait   → 多随机效应预测，生成 .rand
```

所以：

- 要做**真实 IFAM 执行**，必须同时有 R、IFAM.R 和 HIBLUP v1.1.0；缺 HIBLUP 就只能做接口/流程验证。
- 要做**MCP 流程验证**，可以用真实 IFAM.R + fake HIBLUP 的 dry-run，验证参数、命令行、日志、作业、导出和 runner；数值没有科学意义。
- HIBLUP 不能静默换成 v1.7.0：论文与上游 README 固定 v1.1.0，版本变化会影响方差估计/预测与复现结论。

## 目录

| 路径 | 内容 | 状态 |
| --- | --- | --- |
| `skill/ifam-paper/` | 已审校的 Paper2Skill 包：4 个文档 + 6 图 + 3 公式 | `reviewed_with_limitations` |
| `mcp/CONTRACT.md` | IFAM MCP 的工具边界、科学约束、错误码、验收门槛 | draft |
| `mcp/server.py` | 纯 Python MCP stdio 服务（4 工具） | 已实现，未认证 |
| `mcp/ifam_core.py` | inspect、fit 作业、状态、导出 | 已实现；fit 未跑真实 IFAM |
| `mcp/runner.py` | 独立 Pearson/AUC/bias runner | 已实现，合成测试通过 |
| `mcp/dry_run.py` | 真实 IFAM.R + fake HIBLUP 的快速 MCP 流程验证 | 已通过；非科学证据 |
| `mcp/acceptance.py` | tiny + demo 500×5k 的真实执行验收 | 已实现；HIBLUP 阻塞 |
| `mcp/UPSTREAM.md` | 用户下载归档的哈希、demo 表头、参数与输出核对记录 | 已校准，未执行 |
| `mcp/tools.json` | 4 个工具的机器可读 schema | draft |
| `mcp/fixtures/tiny/` | 12 个体 × 24 SNP 的合成夹具及期望检查结果 | 黄金输出测试通过；未执行 IFAM/HIBLUP |

站点的公开预览位于 `site/resources/ifam-paper/`，由
`scripts/build_ifam_skill_preview.py` 生成；不要把站点副本当作源文件，修改应发生
在本目录的 `skill/ifam-paper/`，然后重新生成预览。

## Paper2Skill 的证据

最终构建与严格验证结果：

- 总体状态：`reviewed_with_limitations`；
- `mechanical_ok: true`，`issues: []`；
- 所有页面均已人工审校，`all_sources_agent_reviewed: true`；
- 6 项来源裁定已应用，0 项 stale；
- 9/9 图/公式资源与源裁剪一致；
- 论文正文保留 CC BY 4.0 归属与引用；
- 站点预览的 4 个渲染页已在 1440px 与 390px 检查，6 图 3 公式内嵌显示，
  无横向溢出、破图或控制台错误；ZIP/清单哈希一致。

已记录的局限：

- 没有提供补充材料，`references/supplement.md` 明确记录这一缺失；
- 抽取过程中修复了明显的词连接、DOI 换行和公式字形，但不改变公式含义；
- 论文文本用于阅读与检索，不是基准结果，也不代表作者认证。

## MCP 契约的边界

首批只定义 4 个工具：

1. `ifam_inspect_inputs`：只读检查 PLINK、表型、注释、split、ID 对齐与泄漏；
2. `ifam_fit`：异步调用固定版本的 `Scripts/IFAM.R` + HIBLUP v1.1.0；
3. `ifam_job_status`：轮询状态、阶段、错误和产物；
4. `ifam_export`：只导出标准化预测与 provenance，不计算 Pearson/AUC/bias。

首批 4 个工具已有本地 stdio 实现。指标由 MCP 之外的独立 benchmark runner 计算。
MCP 不接收 held-out truth，不执行任意 R 代码，不拼接外层 shell 字符串，也不接触
UKB/WTCCC 等受限个体级数据。上游 `IFAM.R` 1.0.0 会自动发现注释目录下所有 `*.txt`，
不读取 `annotation_names.txt`；多特殊注释路径在该版本有 bug，首批只支持一个特殊
注释。完整约束、许可冲突和安全限制见 [`mcp/CONTRACT.md`](mcp/CONTRACT.md)，归档
核对见 [`mcp/UPSTREAM.md`](mcp/UPSTREAM.md)，运行方式见
[`mcp/README.md`](mcp/README.md)。

## 合成夹具

`mcp/fixtures/tiny/` 由 `generate.py` 确定性生成，包含：

- 12 个合成个体、24 个 SNP、3 个优化注释 + 1 个特殊注释；
- 注释重叠、1 个缺失基因型、4 个验证 ID 在 fit 表型中为 `NA`；
- 注释目录只有四个自动发现的 `.txt`，没有会被误读的 `annotation_names.txt`；
- 特殊注释以 stem `trait_snps` 传给 `--anno_spec`；
- 期望的 `ifam_inspect_inputs` 结果和所有文件的 SHA-256。

夹具**没有**经过 `IFAM.R`、HIBLUP 或 PLINK 执行。字节级结构、哈希和生成器的
`.bed` 往返检查已通过，但这不能替代真实工具链的验收。详见
[`mcp/fixtures/tiny/README.md`](mcp/fixtures/tiny/README.md)。

## 下一步

1. **上游归档已由用户下载并核对**：`main.zip` SHA-256
   `b66f1a6d…91bd2b`，commit `62f8e4cd…f7649`，`IFAM.R` 哈希
   `1ff7efa4…0e0f11`。demo 表头、注释发现规则、`anno_spec` 和 `.rand` 列名已
   写入 [`mcp/UPSTREAM.md`](mcp/UPSTREAM.md)。
2. **等待用户安装执行环境**（下载由用户执行）：R、`optparse` v1.7.5、
   HIBLUP v1.1.0。PLINK 可选；验收使用独立 Python subsetter。助手不自动下载或安装。
3. 用本地 MCP 跑通 tiny 契约测试；该测试已通过。随后在 `ifam_core` 的 fit 管线
   上运行真实 demo；目前只用 stub 验证过作业管理和导出。
4. 运行 `mcp/acceptance.py`：直接执行上游 demo 子集，再通过 MCP 跑同一输入，
   对比 `genetic_values`，由独立 runner 生成 exploratory 记录。
5. 由独立 runner 计算指标，再讨论 L1 认证；单次运行只能标为 exploratory。

上游许可存在 MIT / GPL-3.0 文件头冲突，解决前不复制或再分发 `IFAM.R`；详见契约。

## 预览构建

需要 Python 3.9+ 与 Python-Markdown 3.x：

```bash
python3 scripts/build_ifam_skill_preview.py
```

脚本会复制 13 个源文件、渲染 4 个阅读页、生成 `ifam-paper-skill.zip` 和
`skill-manifest.json`。它不会下载任何外部资源，也不会把 MCP 夹具放进公开站点。

浏览器检查：

```bash
python3 -m http.server 8765 --directory site
# 打开 http://localhost:8765/
```

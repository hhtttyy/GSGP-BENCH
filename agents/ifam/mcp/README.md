# IFAM MCP（本地 stdio 原型）

状态：**本地 stdio 实现 / draft / 未认证**。四个工具和独立 runner 已实现；tiny
契约夹具通过黄金输出测试，真实 IFAM.R 编排也已用 fake HIBLUP 跑通。500×5k 的真实
HIBLUP 数值执行尚未运行（HIBLUP v1.1.0 暂不可得）。不要把这个状态描述为“已上线
服务”或“L1 结果”。

## 文件

| 文件 | 作用 |
| --- | --- |
| `server.py` | 纯 Python MCP stdio 服务；initialize、tools/list、tools/call |
| `ifam_core.py` | 输入检查、fit 作业、状态、导出；不计算指标 |
| `runner.py` | MCP 之外的独立评测：Pearson、AUC、bias 斜率 |
| `dry_run.py` | 真实 IFAM.R + fake HIBLUP 的快速 MCP 流程验证；非科学证据 |
| `stub_runtime/` | 明确标记的 fake engine，仅用于 dry-run |
| `acceptance.py` | 最小端到端验收：stdio → tiny inspect → demo 500×5k → direct/wrapper 对照 → runner |
| `tools.json` | 4 个工具的机器可读契约 |
| `CONTRACT.md` | 科学/安全边界、错误码、验收门槛 |
| `UPSTREAM.md` | 上游归档哈希与格式核对 |
| `fixtures/tiny/` | 12×24 合成契约夹具 |
| `tests/test_contract.py` | 黄金 inspect、schema/runner 边界、stdio 测试 |

## 当前已验证

```bash
python3 -m unittest discover -s agents/ifam/mcp/tests -v
python3 agents/ifam/mcp/acceptance.py --skip-demo
```

- MCP stdio 握手和 `tools/list` 正常；
- `ifam_inspect_inputs` 对 tiny 夹具与
  [`fixtures/tiny/expected/inspect_inputs.json`](fixtures/tiny/expected/inspect_inputs.json)
  完全一致；
- `ifam_inspect_inputs` 对上游 2,796 个体 × 200,000 SNP 的 demo 输入完成真实读取
  （格式检查，不是模型执行）；
- 独立 Python subsetter 已从 demo 生成 500×5,000 子集，并通过同一 inspect 检查；
- 独立 runner 的 Pearson、AUC、bias 斜率、泄漏拒绝有合成测试；
- **真实 IFAM.R 1.0.0 + fake HIBLUP** 的 MCP 流程已跑通（dry-run）：真实参数、
  注释发现、随机效应合并、`.rand/.vars` 解析、作业状态、导出和 runner 都走到了；
- fake engine 的数值没有科学意义；**没有**真实 HIBLUP 执行证据。

## 快速 MCP 流程验证（不需要 HIBLUP）

```bash
export IFAM_ROOT="$HOME/Downloads/IFAM-main"
python3 agents/ifam/mcp/dry_run.py \
  --driver ifam-r \
  --work-dir /tmp/ifam-mcp-dry-run
```

这会启动真实 MCP stdio 服务，使用真实 `IFAM.R`、真实 tiny 输入和 fake HIBLUP
引擎。输出的 `export.json` 和 runner 结果都在 `/tmp/ifam-mcp-dry-run/`，报告会明确
标注 `execution_mode: stub`、`scientific_evidence: false`。没有 R 时可加
`--driver stub-r`，只验证纯 MCP 管线。

注意：当前安装的是 `optparse 1.8.2`，上游 README 固定 1.7.5。dry-run 已验证 1.8.2
可用；真实 HIBLUP 验收时应把版本写入 provenance，必要时再安装 1.7.5。

## 运行 MCP 服务

```bash
export IFAM_ROOT="$HOME/Downloads/IFAM-main"
export IFAM_MCP_JOB_ROOT="/tmp/ifam-mcp-jobs"
# 如果有必要：
export RSCRIPT="/path/to/Rscript"
export HIBLUP="/path/to/hiblup"

python3 agents/ifam/mcp/server.py \
  --base-root "$PWD/agents/ifam/mcp/fixtures/tiny"
```

`--base-root` 是只读输入挂载根目录；工具的 `input_root` 相对于它。客户端配置示例：

```json
{
  "mcpServers": {
    "ifam": {
      "command": "python3",
      "args": [
        "/absolute/path/agents/ifam/mcp/server.py",
        "--base-root",
        "/absolute/path/data"
      ],
      "env": {
        "IFAM_ROOT": "/absolute/path/IFAM-main",
        "IFAM_MCP_JOB_ROOT": "/tmp/ifam-mcp-jobs"
      }
    }
  }
}
```

MCP 客户端应先 `initialize`，再调用：

1. `ifam_inspect_inputs`：返回 counts、覆盖率、重叠、缺失、checks、warnings；
2. `ifam_fit`：返回 `job_id`，worker 在隔离目录调用固定 `IFAM.R`；
3. `ifam_job_status`：轮询状态和日志尾部；
4. `ifam_export`：返回预测、方差组分、注释摘要、artifacts、provenance；不含指标。

验证集 truth 不经过 MCP；它只交给 `runner.py`。

## 最小执行验收

需要先由用户安装（本仓库不会自动下载）：

- R（macOS 安装包）：<https://cran.r-project.org/bin/macosx/>
- R 包 `optparse`（上游 README 是 v1.7.5；当前 1.8.2 已通过 dry-run）
- HIBLUP v1.1.0：**当前官网下载页只列 v1.7.0，v1.1.0 历史条目没有下载链接**。
  不能用 v1.7.0 静默替代；真实执行验收暂时挂起。

PLINK 不是必需：验收用独立的 Python SNP-major subsetter 从 demo 派生
500×5,000 数据；如果你另外有 PLINK，可做额外的外部 `.bed` 校验。

安装后：

```bash
export IFAM_ROOT="$HOME/Downloads/IFAM-main"
export PATH="/path/to/hiblup-dir:$PATH"

python3 agents/ifam/mcp/acceptance.py \
  --upstream-root "$IFAM_ROOT" \
  --work-dir /tmp/ifam-acceptance \
  --threads 2
```

验收会：

1. 通过真实 MCP stdio 检查 tiny 黄金输出；
2. 用独立 Python subsetter 从上游 demo 派生 500 个体 × 5,000 SNP 的本地子集（不提交）；
3. 直接运行 `IFAM.R`，再通过 MCP 跑同一输入；
4. 对比 direct 与 wrapper 的 `genetic_values`，导出预测；
5. 由独立 runner 读取 held-out truth，生成 `exploratory` 记录。

输出在 `/tmp/ifam-acceptance/acceptance_report.json` 和 `acceptance_report.md`。
即使用例通过，它也只代表**工程验收**，不是站点 L1 认证，不能直接进入排行榜。

## 环境缺失时

```bash
python3 agents/ifam/mcp/acceptance.py --upstream-root "$IFAM_ROOT"
```

会返回 `status: blocked` 并列出缺少的 Rscript/HIBLUP/IFAM_ROOT 或哈希不匹配。
PLINK 缺失只作为 warning，不阻塞 Python subsetter 验收。按提示安装后重跑即可；
下载与安装由用户完成。

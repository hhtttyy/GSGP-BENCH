# SBayesRC MCP（本地 stdio 实现）

状态：**本地 stdio 实现 / draft / 未认证**。六个工具已实现，玩具数据上的 pytest
与独立验收已通过。论文级（UKB ~7M SNP）执行**未**发生。不要把这个状态描述为
“已上线服务”或“已复现论文结论”。

## 文件

| 文件 | 作用 |
| --- | --- |
| `src/sbayesrc_mcp.py` | FastMCP 服务入口；挂载 6 个工具（命名空间 `sbayesrc`） |
| `src/tools/sbayesrc.py` | 工具的 JSON 契约与 `Rscript` 子进程转发 |
| `src/r_scripts/sbayesrc.R` | R 侧分发器：加载 renv 项目并调用 SBayesRC 导出函数 |
| `src/requirements.txt` | Python 运行时依赖（FastMCP 4.0.3、mcp） |
| `renv.lock` | R 库版本锁定清单（restore 目标；不含源码） |
| `tools.json` | 6 个工具的机器可读契约 |
| `CONTRACT.md` | 科学/安全边界、错误码、验收门槛 |
| `UPSTREAM.md` | 上游 commit 与格式核对记录 |
| `fixtures/tiny/` | 60 样本 × 18 SNP × 3 LD block 合成夹具 |
| `USAGE.md` | 面向使用者的安装/配置/工作流说明（包相对路径） |

本目录**不 vendor** 上游 GPL-3.0 源码：只固定 commit 并在运行时调用。

## 当前已验证

```bash
# 单元/契约测试（在客户环境中，需先按 USAGE.md 配好环境）
cd <repo> && sbayesrc-env/bin/python -m pytest tests/code/sbayesrc -q
```

- MCP stdio 握手与 `tools/list` 正常；6 个工具全部暴露；
- 玩具数据上 8 个验收用例（每个工具至少一个）在**两套解释器**下通过；
- 确定性工具（tidy/impute/sbrc_multi/cut_ld 及 prs 的确定性部分）与直接调用 R 包
  的独立参考一致；
- `sbayesrc_run` 与直接参考相比，结构性属性（SNP 集合/顺序、产物 schema、PIP 范围）
  一致，数值因上游无种子 RNG 而不逐位相等；
- 交付 ZIP 在**异目录 + 含空格路径**下解压、重建环境、真实调用通过。

## 运行 MCP 服务

按 [`USAGE.md`](USAGE.md) 配置。要点：把 `P2A_RSCRIPT`、`P2A_R_PROJECT`、
`P2A_PLINK2` 放在 **MCP stdio 启动配置的 env** 中（而非客户端进程）。

```json
{
  "mcpServers": {
    "sbayesrc": {
      "command": "</path/to/python>",
      "args": ["</path/to/sbayesrc-mcp>/src/sbayesrc_mcp.py"],
      "env": {
        "P2A_RSCRIPT": "Rscript",
        "P2A_R_PROJECT": "</path/to/sbayesrc-mcp>/r-runtime",
        "P2A_PLINK2": "plink2"
      }
    }
  }
}
```

## 最小执行验收

需要用户安装（本仓库不会自动下载/vendor）：

- R 4.4.3 + 从固定 commit 构建的 SBayesRC（`BH` 固定 1.84.0）；
- `plink2` 静态二进制（仅 `prs` 需要）。

安装后，用 `fixtures/tiny/` 跑 6 个工具即可验收（命令见 `USAGE.md` 的典型工作流）。

## 环境缺失时

若缺 R/plink2，工具调用会返回 MCP 工具错误并附 R/子进程 stderr 尾部。按
`USAGE.md` 的 prerequisites 安装后重跑；下载与安装由用户完成。

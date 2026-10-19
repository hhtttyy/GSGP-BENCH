# Stub runtime（只用于 MCP 管线测试）

这些文件**不执行 IFAM、HIBLUP 或任何统计计算**，也不读取 truth。仅在
`IFAM_MCP_STUB=1` 的 dry-run 中使用。

| 文件 | 模式 | 作用 |
| --- | --- | --- |
| `Rscript.stub` | `--driver stub-r` | 直接伪造 IFAM.R 的日志和输出文件，验证纯 MCP 管线 |
| `hiblup.fake` | `--driver ifam-r` | 由真实 IFAM.R 调用，伪造 GRM/vars/rand 文件，验证 R 编排 |
| `hiblup` | `--driver ifam-r` | 让上游 `system("hiblup ...")` 能找到 fake engine 的包装器 |
| `hiblup.stub` | `--driver stub-r` | 占位可执行文件 |

`dry_run.py` 会在 export provenance 中写入 `runtime_mode: "stub"` 和
`stub_notice`，报告还会写 `scientific_evidence: false`。这些结果不得作为科学证据、
站点 L1 或论文复现引用。

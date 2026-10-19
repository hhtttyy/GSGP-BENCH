# GSGP-Bench Paper2Agent 本地生成套件

这个套件用于在你自己的电脑上，用 **Paper2Agent** 把论文和代码转换成 Skill / MCP。
GSGP-Bench 网站不执行任何生成任务，也不接收论文文件或原始数据。

## 前置条件

- 一个支持 skills、shell 和并行子 Agent 的编码 Agent（Claude Code、Codex 等）；
- Git 和 Python；
- 论文代码需要的 R、原生 CLI、数据或 GPU 环境；
- 论文/代码的使用许可，以及可公开或可合成的测试数据。

## 安装

1. 解压 `paper2agent-local-kit.zip`；
2. 把顶层的 `paper2agent/` 目录复制到你的 Agent skills 目录；
3. 重启 Agent，确认能看到 paper2agent skill。

不同 Agent 的 skills 目录不同，以宿主文档为准。

## 使用

把 [`PROMPT.md`](Paper2Agent-Prompt.md) 中的提示词复制给 Agent，并填入：

- 论文 PDF/链接/本地文件；
- 代码仓库或本地路径；
- 输出目录；
- 希望聚焦的方法/任务/tutorial。

Agent 会生成 Paper2Skill、MCP 包、运行说明和验证记录。你必须自己在本地运行测试并检查结果。

## 交付后

1. 检查生成的 Skill/MCP 是否包含论文、代码、许可证和限制；
2. 在本地用公开或合成数据跑一次；
3. 通过网站 [提交 MCP](../site/resources/submit/index.html) 对应的 GitHub Issue 模板提交；
4. 中央团队验证后给出 **已认证 / 未认证**。

## 注意

- 不要让 Agent 下载或上传受限数据（UKB、WTCCC、私有育种数据等）；
- 不要执行不可信的任意代码；
- 生成成功不等于认证成功；
- 认证的是包，不是论文结果，也不代表我们在线托管 MCP。

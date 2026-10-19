# Paper2Agent 本地生成提示词

复制下面这段给支持 skills 的编码 Agent（Claude Code、Codex 等）：

```text
Read the paper2agent skill and use it to agentify this paper and its code.

Paper and associated files:
- <PAPER_PDF_OR_URL_OR_LOCAL_PATH>

Code repository (if available):
- <GITHUB_URL_OR_LOCAL_PATH>

Output directory:
- <PROJECT_DIR>

Task focus (optional):
- <METHOD / TUTORIAL / SOURCE_URL>

Requirements:
1. Follow the paper2agent workflow: paper understanding, code audit,
   Skill/MCP generation, runtime verification, and final delivery.
2. Keep the paper, code, and generated artifacts traceable.
3. Do not download or upload restricted data.
4. Do not execute untrusted code outside the isolated project environment.
5. Record runtime versions, commands, test data, and known limitations.
6. The MCP must not receive held-out truth and must not compute benchmark metrics.
7. Produce a package that can be submitted to GSGP-Bench for MCP certification.
```

生成后，按 `LOCAL_KIT_README.md` 的步骤检查并提交。

# MCP 认证规则（简化版）

> 只保留两个状态：**已认证** / **未认证**。  
> 认证的是用户提交的 MCP 包，不是论文结果，也不代表网站在线托管或执行它。
> 认证只看包的行为和来源可追溯，不要求由 Paper2Agent 生成；手动、Paper2Agent 或其他工具生成的包都可以提交。

## 1. 两个状态

| 状态 | 含义 | 网站展示 |
| --- | --- | --- |
| **已认证** | GSGP-Bench 中央团队实践验证过这个版本的 MCP 包 | `已认证` 徽章 + 测试摘要 |
| **未认证** | 用户上传了，但中央团队尚未完成/通过验证 | `未认证` 徽标；仍可被查看和使用，风险自担 |

MCP 认证只有两个状态，不再引入其他层级：

> 已认证 = 这个 MCP 包在固定版本和参考数据上通过我们的检测；它不是结果认证，也不是在线服务。

## 2. 已认证的最低检测项

中央团队收到包后统一检查：

1. 有来源：论文 DOI、代码仓库、commit、许可证；
2. 有 MCP 契约：工具、输入、输出和版本；
3. 能启动：stdio/HTTP 说明清楚，客户端可以调用；
4. 能跑参考数据：至少一组公开或合成测试数据；
5. 能产出预测/结果文件，字段符合约定；
6. 不接收 held-out truth，不在 MCP 内计算 benchmark 指标；
7. 与直接运行/参考实现对比，差异在容差内；
8. 不执行任意用户代码，不访问受限数据；
9. 有清晰的限制、失败模式和联系方式。

任一项不满足 = **未认证**，但页面可以保留条目并提示风险。

## 3. 谁运行、谁托管

- 我们不托管在线 MCP 服务。
- 用户下载/安装 MCP，在自己的 Agent 或本地环境使用。
- 网站只展示包信息、认证状态、测试摘要和结果记录。
- “已认证”不等于“在线可用”，也不等于“结果已被科学认证”。

## 4. 提交方式

用户先通过网站的本地生成页 `site/resources/generate/index.html` 下载 Paper2Agent 套件，在自己的 Agent 中生成 Skill/MCP，再通过仓库的
`.github/ISSUE_TEMPLATE/mcp-submission.yml` 提交：

```text
论文 / DOI
代码仓库 / commit / license
Skill、MCP 包或路径
运行方式 / 依赖
测试命令
参考数据
期望产物
truth 是否隔离
已知限制
```

中央团队验证后：

- 通过 → 标记 **已认证**，增加测试摘要和版本；
- 未通过 → 保持 **未认证**，公开可见、可用，但明确风险。

## 5. 当前条目

| MCP | 状态 | 说明 |
| --- | --- | --- |
| GBLUP baseline MCP | **已认证** | 中央测试通过：inspect/fit/export、direct 对照、schema；结果仍为 EXP |
| IFAM MCP | **未认证** | 本地 stdio 原型；fake HIBLUP STUB；真实 HIBLUP 未验证 |
| 其他用户上传 | 未认证 | 可见、可用、风险自担；等待验证 |

## 6. 结果等级仍单独记录

MCP 认证与结果等级是两件事：

- MCP：已认证 / 未认证；
- 结果：`demo` / `stub` / `EXP` / `L1` / `L2` / `L3`。

“MCP 已认证”不会自动把某次运行升级为 L1。结果等级仍见
[`docs/证据等级与记录.md`](证据等级与记录.md)。

## 7. 相关文件

- GBLUP 认证记录：`benchmark/algorithms/gblup/certification.json`
- GBLUP 工具契约：`benchmark/algorithms/gblup/tools.json`
- GBLUP Skill：`benchmark/algorithms/gblup/SKILL.md`
- 结果 schema：`benchmark/schema/result.v1.json`
- 提交模板：`.github/ISSUE_TEMPLATE/mcp-submission.yml`
- 网站介绍页：`site/resources/introduce/index.html`

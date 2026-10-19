# IFAM 上游归档核对记录

> 快照：2026-10-18。归档由用户下载并保存在仓库外；本仓库只记录哈希与核对结论，
> 不包含上游压缩包、demo 数据或输出。

## 1. 归档

| 项 | 值 |
| --- | --- |
| 来源 | `https://github.com/xiaolei-lab/IFAM/archive/refs/heads/main.zip` |
| 本地路径 | `~/Downloads/IFAM-main.zip`（仓库外） |
| ZIP 大小 | 23,259,174 bytes |
| ZIP SHA-256 | `b66f1a6d9b01115d955552a1252a4ea3d22ad25b335fce1fcf8b41ba8a91bd2b` |
| ZIP 注释中的 commit | `62f8e4cd8ee53d70b3324ec5cd40d3f2ffbf7649` |
| 解压顶层目录 | `IFAM-main/` |
| 处理方式 | 解压到 `/tmp/ifam-upstream-b66f1a/` 做只读检查；未执行 R/HIBLUP |

## 2. 文件哈希

| 文件 | SHA-256 |
| --- | --- |
| `LICENSE` | `b4dd821d1f675e271e94227834924ec8e01e3b32db1c57ae4debac7976adb39a` |
| `README.md` | `9888125bccb2a9574b5c7c69a9ea248808041a1137f596b180cae9696d89ec8c` |
| `Run_demo_Script.R` | `3f495a1c7c6e6d2208fd882283646963ba26fece42e864632f1e26fdd65e232d` |
| `Scripts/EA.R` | `4a52424f49a7b1b538cc575e13d1b011695760a7926711930a87489d7e7111aa` |
| `Scripts/IFAM.R` | `1ff7efa4e0ecaf2c4998202a3e5658e5cc2987878f3304479e39d18d210e0f11` |
| `demo_data.zip` | `6345f034eaaf4738ea8e61018c2b53010419512f12e717e92b94dadd44f495df` |
| `output.zip` | `475b02504d5ba91f58fe33330bdd3b0430607b149f2143a215a878a5689899be` |

`demo_data.zip` 解压后 21 个条目、152,291,937 bytes；`output.zip` 32 个条目、
762,093 bytes。两者只用于格式核对，未放入本站。

## 3. 已核对的事实

### 3.1 输入

- `IFAM.R` 打印版本为 `1.0.0`，依赖 R、`optparse` v1.7.5、HIBLUP v1.1.0。
- 注释目录中的 **所有直接 `*.txt` 文件**都会被 `list.files()` 当作注释；
  脚本不读取 `annotation_names.txt`。上游 README 关于该清单的说法与代码不符。
- 注释文件为一列、无表头 SNP ID；基因型为 PLINK 1 二进制三件套。
- 表型文件首行是表头，第 1 列是 ID，表型列由 `--pheno_pos` 选择。demo 表头为
  `Geno.id` 与 `T1`，因此 ID 列名不是固定值。
- `--anno_spec` 接收**不带 `.txt` 的注释名**，例如 `A8`，内部再拼成
  `<anno_folder>/A8.txt`。多个特殊注释的代码路径在 1.0.0 中有缺陷：多值分支
  没有给 `anno_spec_file` 赋值，随后构造矩阵会失败。因此首批契约只支持一个特殊
  注释。
- `--outPath` 必须是已存在目录，并以 `/` 结尾；脚本直接把它与输出前缀拼接。
- `--tmp_files FALSE` 会执行通配符 `rm <outPath><prefix>**`，不适合作为包装层
  的清理机制。包装层应始终传 `TRUE`，再按自己的保留策略清理作业目录。
- 脚本内部用字符串拼接调用 `hiblup`、`wc` 和 `rm`（`system()`）。包装层不是
  “上游完全无 shell”：必须限制路径和注释名的字符集，并保持脚本版本固定。

### 3.2 输出

- `*.annotaion.information.txt`（上游拼写）表头为
  `Annotations	Number_annotaions	Number_overlap_anno_map	Anno_cover_percent`。
- `*.overlaped.SNPs.between.anntations.txt`（上游拼写）为注释两两重叠矩阵。
- `*_<trait>.rand` 的列依次为：个体 ID、每个随机效应的预测值、
  `genetic_values`（各随机效应之和）、`residuals`。
- `*_<trait>.vars` 是最终模型的方差组分，包含每个随机效应和 `e`。
- `*_<trait>_vc.vars` 是优化前的逐注释方差估计；脚本随后删除 `_vc.beta` 和
  `_vc.rand`。
- `IFAM.R` 不做交叉验证，也不计算 Pearson、AUC 或 prediction bias。

### 3.3 输出文件的实测核对

使用归档 `output.zip` 中的 basic/advanced 结果做只读解析（这些是上游随包提供的
历史输出，不是本项目的独立运行）：

- 两份 `IFAM_T1.rand` 都是 2,796 行；列依次为 `ID`、两个随机效应列、
  `genetic_values`、`residuals`；
- 对每一行，随机效应列之和与 `genetic_values` 一致：basic 最大绝对差为 0，
  advanced 为 `4.44e-16`（浮点舍入）；
- `.vars` 与 `_vc.vars` 的表头都是
  `Item	Var	Var_SE	h2	h2_SE	h2_Pr(Chisq)`；
- `IFAM.annotaion.information.txt` 有 8 个注释行，表头与 §3.2 一致；
  `IFAM.overlaped.SNPs.between.anntations.txt` 是 8×8 重叠矩阵。

因此 `ifam_export` 可以直接读取 `ID` 与 `genetic_values`，不需要重算随机效应和；
仍应在 wrapper 中验证列存在、行数非零、ID 唯一，并保留原始 `.rand` 作为 artifact。

## 4. 需要保留的上游问题

1. **许可表述冲突**：仓库 `LICENSE` 是 MIT，论文也写 MIT；但
   `Scripts/IFAM.R` 文件头声明 GPL-3.0。当前不复制、不修改、不再分发该脚本，
   只在运行时调用固定版本；在完成法律核对前，不要把脚本 vendor 进本仓库或
   镜像。
2. **多特殊注释 bug**：见 3.1，首批限制为一个。
3. **README 与代码不一致**：README 提到 `annotation_names.txt`，代码实际扫描
   所有 `*.txt`；若放入该文件，它会被当作一个注释。
4. **Zenodo DOI 不一致**：论文为 `10.5281/zenodo.18802709`，README 为
   `10.5281/zenodo.18802710`；以 commit 为代码锚点，两个 DOI 都保留在溯源信息
   中，待解析。
5. **HIBLUP v1.1.0 不易获得**：2026-10-19 检查 `hiblup.com/downloads`，当前只提供
   v1.7.0；版本历史虽列出 v1.1.0，但没有可用的归档链接。不能用 v1.7.0 静默替代。
   当前用真实 `IFAM.R` + fake HIBLUP 做 MCP dry-run；真实数值验收暂时挂起。
6. **未执行验证**：R 4.6.1 + optparse 1.8.2 已安装；HIBLUP 尚未安装，尚未跑通 demo；
   不能把格式核对或 fake engine dry-run 当作执行成功。

## 5. 仍未完成

- 安装 R、`optparse` v1.7.5、HIBLUP v1.1.0（由用户下载安装）；PLINK v1.90 可选，
  用于额外 `.bed` 外部校验。
- 运行上游 `Run_demo_Script.R` 的 basic/advanced 流程，保存日志、退出码和产物
  哈希。
- 验证 HIBLUP 对 `NA` 表型个体的预测输出，确认验证集覆盖。
- 用 PLINK 验证 tiny `.bed`。
- 实现 MCP wrapper，并执行 `CONTRACT.md` 的验收项。

# tiny 合成夹具

60 样本 × 18 SNP × 3 LD block 的**确定性合成数据**，用于 SBayesRC MCP 的工程验收。
不含任何真实个体数据，可自由分发。

| 路径 | 内容 |
| --- | --- |
| `geno/toy_bfile.{bed,bim,fam}` | PLINK 1 二进制基因型（60×18）|
| `ld/` | SBayesRC LD 参考（`snp.info`、`ldm.info`、`block*.eigen.bin`、`b*.ldm.full.*`）|
| `summary/toy.ma` | COJO 格式 GWAS 汇总（18 SNP）|
| `annotations/toy_annot.txt` | 3 列注释（Intercept/Coding/Conserved）|
| `pheno/toy_pheno.txt` | 表型（前 45 个体为 0，后 15 为 1）|
| `pheno/toy_tune.id` | sbrcMulti 的调优样本 ID |

生成脚本 `gen_toy.R`、`build_toy_ld.R` 保留以溯源；`run_reference.R` 是**不经 MCP**
直接调用 SBayesRC R 包的独立参考路径。哈希见 [`../../UPSTREAM.md`](../../UPSTREAM.md) §3。

> 该夹具上通过只代表工程验收，不是科学结论。

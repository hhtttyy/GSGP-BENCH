# Supplementary information

# nature genetics

Article

https://doi.org/10.1038/s41588-024-01704-y

Leveraging functional genomic annotations and genome coverage to improve polygenic prediction of complex traits within and between ancestries

In the format provided by the authors and unedited

# Table of Contents

Supplementary Note ......................................................................................................... 2
1. Summary-data-based low-rank model .................................................................................. 2
2. Advantages of using low-rank model .................................................................................... 4
3. Estimation of residual variance helps to improve model robustness ...................................... 5
4. Low-rank model does not disturb Bayesian learning on the annotation effects ...................... 6
5. Alternative parameterization for π ....................................................................................... 7
6. Scaling the SNP marginal effect estimates ............................................................................. 8
7. Estimation of SNP-based heritability and per-SNP heritability enrichment for each annotation
................................................................................................................................................ 9
8. MCMC sampling scheme..................................................................................................... 10
9. Calibrating parameters for the low-rank model ................................................................... 14
10. Tuning for the optimal eigenvalue cut-off ......................................................................... 14
11. Violation of model assumptions ........................................................................................ 17
12. Sensitivity analysis in simulation for SBayesRC .................................................................. 17
13. Simulation under the S-LDSC/MegaPRS model .................................................................. 18
14. Difference between the LDSC/MegaPRS model and SBayesRC model................................. 18
15. Comparison between SBayesRC and MegaPRS .................................................................. 19
16. Other factors affecting accuracy of prediction leveraging functional annotations ............... 20
17. Summary data imputation ................................................................................................ 22
18. Running settings for the cross-validation in the UKB .......................................................... 22
19. Running settings for trans-ancestry prediction .................................................................. 23
20. Reason for using cross-validation in the UKB analysis ........................................................ 24
21. Acknowledgements .......................................................................................................... 25
Supplementary Figures ................................................................................................... 27
Reference ....................................................................................................................... 44

# Supplementary Note

## 1. Summary-data-based low-rank model

To simultaneously analyse all common variants, SBayesRC utilises a low-rank model based on the eigen-decomposition on quasi-independent LD blocks in the human genome1. In each LD block k, the summary-data-based model (as used in SBayesR) is transformed into a new model where the joint effects of mk SNPs are fitted to qk linear combinations of marginal SNP effects (instead of mk marginal SNP effects), with qk being the number of top principal components (PCs) that collectively explain at least a given proportion (𝜌) of variance in the LD matrix (Extended Data Fig. 1a). In this model, the dimension of the system of equations is qk  mk, with qk much smaller than mk, which reduces memory consumption and speeds up computation significantly. For instance, when 𝜌= 99.5%, qk/mk ≈ 0.2 on average across LD blocks for the 7.4 million common SNPs used in this study (Supplementary Fig. 1). Essentially, the low-rank model refines the signals in GWAS summary statistics by collapsing information from SNPs in high LD. In addition to the computational advantages, the low-rank transformation enhances model robustness by 1) removing small PCs that are subject to LD differences between GWAS and reference samples, and 2) enabling a Gibbs sampling algorithm to directly estimate the residual variance, a nuisance parameter accommodating remaining LD variations and potential errors in GWAS summary data.

We derive a summary-data-based low-rank model from a general form of individual-level linear regression. Consider model

[Formula on PDF page 3](../assets/supp_figs/s002-formula-p0003-004.jpg)

where y is the vector of trait phenotypes adjusted for covariates, such as sex, age and principal components (PCs), X is the genotype matrix of m SNPs standardised to have column mean zero and variance one, 𝜷 is the vector of true SNP effects, and 𝐞 are the residuals with 𝑉𝑎𝑟(𝐞) = 𝐈𝜎𝑒 2. Let N be the sample size. Multiplying both sides of the equation by 1 𝑁𝐗′ gives

[Formula on PDF page 3](../assets/supp_figs/s002-formula-p0003-006.jpg)

The left-hand side is the GWAS marginal effect estimates b. Let 𝐑= 1 𝑁𝐗′𝐗 be the LD correlation matrix. Then, we have

[Formula on PDF page 3](../assets/supp_figs/s002-formula-p0003-008.jpg)

This is the summary-data-based model underlying many methods. Of note, in this model, the residuals have a variance-covariance structure proportional to the LD matrix, i.e.,

𝑉𝑎𝑟( 1 𝑁𝐗′𝐞) = 1 𝑁𝐑𝜎𝑒 2. It is often neither feasible nor necessary to compute the whole- genome LD matrix. Alternatively, we compute R for each of the LD blocks that are found to be approximately independent in the human population. In this case, the genome-wide LD matrix is a block-diagonal matrix with blocks defined by LD blocks. The eigen- decomposition of Ri for block i, which can be performed independently and in parallel between block, is (the subscript is ignored for simplicity in notation)

[Formula on PDF page 4](../assets/supp_figs/s002-formula-p0004-002.jpg)

where U is the matrix of eigenvectors and 𝚲 is the diagonal matrix of eigenvalues. Substitution of R in the equation above gives

[Formula on PDF page 4](../assets/supp_figs/s002-formula-p0004-004.jpg)

Multiplying both sides by 𝚲−𝟏 𝟐𝐔′ gives

[Formula on PDF page 4](../assets/supp_figs/s002-formula-p0004-006.jpg)

or simply,

[Formula on PDF page 4](../assets/supp_figs/s002-formula-p0004-008.jpg)

where 𝐰= 𝚲−𝟏 𝟐𝐔′𝐛 is a linear combination of marginal SNP effect estimates, 𝐐= 𝚲 𝟏 𝟐𝐔′ is the new coefficient matrix, and the new residuals 𝝐= 1 𝑁𝚲−𝟏 𝟐𝐔′𝐗′𝐞 are independently and identically distributed, i.e.,

[Formula on PDF page 4](../assets/supp_figs/s002-formula-p0004-010.jpg)

Due to LD between SNPs and limited sample size, the LD matrix estimated from a reference sample is often rank deficient. In this case, a number of eigenvalues are zero. Additionally, small eigenvalues are subject to sampling variation in LD between GWAS and LD reference samples. To this end, we partition 𝚲 into

[Formula on PDF page 4](../assets/supp_figs/s002-formula-p0004-012.jpg)

where 𝚲𝑞 contains q eigenvalues in descending order that cumulatively explain at least a

given proportion (𝜌) of variance in LD, i.e., 𝜌= ∑ Λ𝑖 𝑞 𝑖=1 ∑ Λ𝑖 𝑚 𝑖=1 where Λ𝑖 is the ith nonzero

eigenvalue, and 𝚲0 contains remaining eigenvalues including zeros. Then the model can be written as

[Formula on PDF page 5](../assets/supp_figs/s002-formula-p0005-001.jpg)

To remove the noise in LD, we discard the equations for 𝐰0, resulting in a low-rank model:

[Formula on PDF page 5](../assets/supp_figs/s002-formula-p0005-003.jpg)

where 𝐐𝑞 has a dimension of 𝑞× 𝑚 with 𝑞≪𝑚. In essence, the true SNP effects are fitted to a smaller number of effective data points rather than the observed data points that are highly correlated to each other. This model is general and can be applied with different assumptions on the distribution of SNP effects 𝜷.

# 2. Advantages of using low-rank model

We proposed a rank reduction approach to account for correlations between marginal effects, allowing the joint effects of genome-wide SNPs to be fitted to a set of observables with independent residuals. There are several advantages of using this low-rank model. First, it substantially improved the model robustness. We showed that our method is robust to LD differences between GWAS and reference samples, as well as per-SNP sample size variations resulted from the meta-analysis between cohorts with different genotyping platforms. As shown in the real trait analysis (Fig. 3b, Fig. 4c,d, and Extended Data Fig. 7), SBayesRC consistently yielded robust prediction accuracy, when using an external LD reference independent of the GWAS sample, outperforming other methods. We recommend using in- sample LD for improved prediction accuracy, but when this is not possible, SBayesRC is expected to exhibit greater robustness compared to other methods. The low ranking is not only due to the elimination of many small eigenvalues/eigenvectors in each LD block, which are subject to high sampling variation in LD, but also because the independence of transformed summary statistics enables the sampling of block-wise residual variance, which introduces a mechanism to manage the convergence issue caused by violations of model assumptions (Supplementary Note 3). It has been found that SNP effect sizes can blow up during MCMC when the model fails to converge. In this case, the sampled values of residual variances would be large, causing the SNP effect sizes to shrink back toward zero, thereby preventing convergence failure. Second, the low-rank model substantially improved the computational efficiency, which allows us to fit a large number of SNPs with only a small fraction of computation resource compared to the original model. In theory, SBayesRC is scalable to fit variants at the sequence level via calibrating the required proportion of

variance in LD explained by the selected eigenvalues/eigenvectors, making it a powerful tool to analyse the incoming large-scale whole-genome sequence data. Third, this low-rank model depicts a general framework that can be applied with different priors, as used in other methods.

3. Estimation of residual variance helps to improve model robustness In the summary-data-based model, Eq (1), 𝑉𝑎𝑟(𝜺) = 1 𝑁𝐑𝜎𝜖 2. It is often assumed that 𝜎𝜖 2 ≈𝜎𝑦 2 given a negligible proportion of variance explained by a single SNP, and further 𝜎𝜖 2 ≈1 assuming a unit phenotypic variance for the trait. It is possible, however, that 𝜎𝜖 2 > 1 if there exist large LD differences between GWAS and LD reference samples. This is because using summary statistics from GWAS and inaccurate LD data from a reference is analogous to using estimated genotype data with noise in the fitted model for GWAS:

[Formula on PDF page 6](../assets/supp_figs/s002-formula-p0006-002.jpg)

where 𝐗̂ is the combination of genotypes used in GWAS (X) and the differences to those observed from the reference (𝚫), and 𝑏̂ is the ordinary least squares estimate for the SNP effect. It can be seen that the new residual in the above model can have variance larger than the phenotypic variance when the noise in the genotype data is large, i.e., 𝑉𝑎𝑟(Δ𝑏̂ + e) > Var(𝑦). Thus, it would be beneficial to estimate the residual variance from the data given the GWAS summary statistics and reference LD data.

In contrast to Eq (1), it is very straightforward to estimate the residual variance in the low- rank model, Eq (2), because the residuals are independently distributed, 𝑉𝑎𝑟(𝝐) = 1 𝑁𝐈𝜎𝜖 2. The MCMC sampling process for the residual variance is shown as below. The large residual variance estimate will introduce a shrinkage mechanism to manage the potential convergence issue due to violation of model assumptions. It has been found that SNP effect sizes would blow up during MCMC when the model fails to converge. In this case, the sampled values of residual variances would be large if the SNP effect sizes tend to blow up, which will in turn shrink them back toward zero, preventing the failure in convergence.

4. Low-rank model does not disturb Bayesian learning on the annotation effects

An annotation-dependent prior is used in SBayesRC to better model the distribution of SNP effects and to learn both annotation parameters and SNP effects from the data. In SBayesR, SNP effects follow a mixture of normal distributions with different variances, including a point mass at zero, capturing various genetic architectures. However, it is independent of genomic features, such as LD and minor allele frequency (MAF) patterns and biological functions of different genomic regions. In SBayesRC, the probability parameters of the mixture distribution are estimated from a generalised linear model with individual SNP annotations as independent variables (Extended Data Fig. 1b). Both binary and quantitative annotations are accommodated, regardless of overlap between them. This approach describes the probability that SNPs are causal variants and the probability distribution of their effect sizes, better capturing the causal effects if the distributions of effect sizes truly differ between annotations. It is of note that the Bayesian learning machinery on the annotation effects is not disturbed by the low-rank reduction at the level of summary data.

The low-rank model is derived from the standard summary-data-based model, where m SNP marginal effects (b) are fitted with m SNP joint effects (𝜷):

[Formula on PDF page 7](../assets/supp_figs/s002-formula-p0007-003.jpg)

with R being a mm matrix and 𝜺 being mutually correlated with a variance-covariance

matrix proportional to R. In each LD block, we perform eigen-decomposition on R such that

𝐛= 𝐔𝚲𝐔′𝜷+ 𝜺                                                          (3)

where U and 𝚲 are matrices of eigenvectors and eigenvalues, respectively. The low-rank model is constructed such that the dimension of observed data (b and R) is reduced but the dimension of parameters (𝜷) remains. In essence, it fits q observables with m SNP joint effects, where q<<m and the observables are correlated only through SNP joint effects but not residuals:

# 𝐰= 𝐐𝜷+ 𝝐

with 𝐰 being a q1 vector and 𝐐 being a qm matrix. As shown in our simulation and real data analyses, the low-rank model approximates the standard model with high accuracy, when the choice of q is well calibrated, and has considerable improvement in computational efficiency and robustness. The functional annotations are incorporated into the prior distribution of 𝛽𝑗:

[Formula on PDF page 8](../assets/supp_figs/s002-formula-p0008-000.jpg)

[Formula on PDF page 8](../assets/supp_figs/s002-formula-p0008-001.jpg)

with 𝐀𝑗 being the observed annotation data matrix for SNP j and 𝜶𝑘 being the vector of unknown annotation effects estimated from the data. In this model, functional annotations describe the prior distribution of SNP joint effects, thereby contributing to the posterior estimation of SNP weights. It is a hierarchical Bayesian learning process for 𝜶𝑘 because 𝜶𝑘 connect to the data (w and Q) only through 𝜷, which means that 𝜶𝑘 can be estimated in either the standard model (1) or the low-rank model (2) since both models have 𝜷 as parameters. Note that an alternative reduction is to reduce the dimension of parameter space, that is, from Eq (3) we can have

[Formula on PDF page 8](../assets/supp_figs/s002-formula-p0008-003.jpg)

where U is a mq matrix and 𝜷∗= 𝚲𝐔′𝜷 becomes a q1 vector that captures the principal component effects. In this case, the Bayesian machinery to learn about the different weights associated with functional annotations would not work because each element of 𝜷∗ is not the SNP joint effect itself but a linear combination of SNP joint effects.

In summary, the Bayesian learning about functional annotations works in the low-rank model because the low rank approximation still captures >99% of the variance. However, it is expected that with a lower eigenvalue threshold (e.g., 50%), the performance would be compromised.

# 5. Alternative parameterization for 𝝅

To remove the dependence between elements of 𝝅𝑗 for each SNP, we employed an alternative parameterization for modelling membership probabilities and annotation effects. Let 𝛿𝑗 be the indicator for the mixture component membership for SNP j:

[Formula on PDF page 8](../assets/supp_figs/s002-formula-p0008-008.jpg)

We define a conditional probability that the SNP effect belongs to the kth distribution given that it has passed the bar for the (k-1)th distribution as

[Formula on PDF page 8](../assets/supp_figs/s002-formula-p0008-010.jpg)

such that

[Formula on PDF page 8](../assets/supp_figs/s002-formula-p0008-012.jpg)

[Formula on PDF page 9](../assets/supp_figs/s002-formula-p0009-000.jpg)

We then apply the generalised linear model to link 𝑝𝑗𝑘 with 𝜶𝑘, i.e.,

[Formula on PDF page 9](../assets/supp_figs/s002-formula-p0009-002.jpg)

In this parameterisation, all 𝑝𝑗𝑘 are independent, which means that 𝜶𝑘 can be sampled in parallel in each MCMC iteration, and 𝛼𝑘𝑐 can be sampled from its full conditional distribution using Gibbs sampling algorithm, following the algorithm of Albert and Chib2.

Let 𝑧𝑗𝑘 be the indicator variable for whether the SNP effect can “climb” up to a higher distribution, i.e.,

[Formula on PDF page 9](../assets/supp_figs/s002-formula-p0009-005.jpg)

To allow Gibbs sampling, a probit link function is chosen, namely 𝑔−1(𝑝𝑗𝑘) = Φ(𝑝𝑗𝑘) where Φ(∙) is the cumulative density function (CDF) of the standard normal distribution. It has been shown that with an auxiliary variable 𝑙𝑗𝑘 defined as

[Formula on PDF page 9](../assets/supp_figs/s002-formula-p0009-007.jpg)

a linear model can be constructed as

[Formula on PDF page 9](../assets/supp_figs/s002-formula-p0009-009.jpg)

with 𝜀𝑗𝑘 ~ 𝑁(0,1). In this model, given a normal prior distribution, 𝛼𝑘𝑐 ~ 𝑁(0, 𝜎𝛼𝑘 2 ), the full conditional distribution for 𝛼𝑘𝑐 is a univariate normal distribution, since 𝛼𝑘𝑐 is conditionally independent of 𝒛𝑘 given 𝒍𝑘. Given 𝑧𝑗𝑘 and 𝜶𝑘, the full conditional distribution for the latent variable 𝑙𝑗𝑘 is a truncated normal distribution. The Gibbs sampling procedure is described in the following section.

# 6. Scaling the SNP marginal effect estimates

The derivation for the summary-data-based model is based on the marginal effects in units of per standardized genotype (b). When the marginal effects were estimated from GWAS using genotypes at 0/1/2 scale (b*), b can be estimated, in a scalar form, by

[Formula on PDF page 10](../assets/supp_figs/s002-formula-p0010-000.jpg)

where 𝜎𝑦 2 is the phenotypic variance, 𝑁𝑗 is the per-SNP sample size, and 𝜎𝑗 is the standard error for SNP j. If the trait phenotypes are not standardized, the phenotypic variance can be estimated by taking the median value of 2𝑓𝑗(1 −𝑓𝑗) [𝑁𝑗𝜎𝑗 2 + (𝑏𝑗 ∗) 2] across SNPs, where 𝑓𝑗 is the allele frequency in the GWAS sample (ref3,4). The per-SNP sample size 𝑁𝑗 can be replaced by the overall sample size N. Here, we assume 𝜎𝑦 2 = 1, then

[Formula on PDF page 10](../assets/supp_figs/s002-formula-p0010-002.jpg)

and will scale the joint effect estimate 𝛽𝑗 back to the phenotypic scale using the same 𝑠𝑗 so that this parsimonious assumption would not have an impact on the result (ref.5,6).

# 7. Estimation of SNP-based heritability and per-SNP heritability enrichment for each annotation

The total genetic variance is

[Formula on PDF page 10](../assets/supp_figs/s002-formula-p0010-006.jpg)

We calculate this quantity in each of MCMC iterations given the sampled values of SNP effects 𝜷. Assuming unit phenotypic variance, the SNP-based heritability ℎSNP 2 = 𝜎𝑔 2, estimated by the posterior mean of MCMC samples discarding the samples from the burn-in period.

For a binary annotation c, the total variance explained by the SNPs within the annotation is calculated as

[Formula on PDF page 10](../assets/supp_figs/s002-formula-p0010-009.jpg)

where 𝑚𝑐 is the number of SNPs within the annotation. The per-SNP heritability enrichment (𝜃𝑐) is then calculated as

[Formula on PDF page 11](../assets/supp_figs/s002-formula-p0011-000.jpg)

For a quantitative annotation, the per-SNP heritability enrichment is calculated as the slope of the regression of 𝛽𝑗𝑐 2 on the annotation value 𝐴𝑗𝑐

[Formula on PDF page 11](../assets/supp_figs/s002-formula-p0011-002.jpg)

and 𝜃𝑐= 1 + 𝜔𝑐. Similarly, we compute 𝜃𝑐 in every iteration of MCMC and estimate by the posterior mean after burn-in.

# 8. MCMC sampling scheme

We use MCMC sampling to draw posterior inference on the model parameters. The joint distribution of data and all parameters in the low-rank model is

[Formula on PDF page 11](../assets/supp_figs/s002-formula-p0011-006.jpg)

Suppose 𝛿𝑗 is the indicator variable to the distribution membership of 𝛽𝑗. The full conditional distribution for 𝛽𝑗 is

[Formula on PDF page 11](../assets/supp_figs/s002-formula-p0011-008.jpg)

where

[Formula on PDF page 12](../assets/supp_figs/s002-formula-p0012-000.jpg)

The full conditional distribution for 𝛿𝑗 is

[Formula on PDF page 12](../assets/supp_figs/s002-formula-p0012-002.jpg)

where 𝑓(𝐰|𝛿𝑗= 𝑘, 𝜷, 𝜎𝑔 2,𝜎𝜖 2) is shown as above and 𝑓(𝛿𝑗= 𝑘) = 𝜋𝑘.

As described above, 𝝅𝑗 is a function of 𝒑𝑗, and 𝒑𝑗 is a linear model of 𝜶𝑘 through the probit link, i.e.,

[Formula on PDF page 12](../assets/supp_figs/s002-formula-p0012-005.jpg)

Here, we introduce another indicator variable 𝑧𝑗𝑘, where

[Formula on PDF page 12](../assets/supp_figs/s002-formula-p0012-007.jpg)

and a latent variable 𝑙𝑗𝑘, for which the full conditional distribution is

[Formula on PDF page 12](../assets/supp_figs/s002-formula-p0012-009.jpg)

Similar to the sampling of SNP effects, we use single-site Gibbs sampler to sample the annotation effects. The full conditional distribution for 𝛼𝑘𝑐 is

𝑓(𝛼𝑘𝑐|𝒍𝑘,𝜶−𝑘𝑐,𝜎𝛼𝑘 2 )

[Formula on PDF page 12](../assets/supp_figs/s002-formula-p0012-012.jpg)

where

[Formula on PDF page 12](../assets/supp_figs/s002-formula-p0012-014.jpg)

The full conditional distribution for 𝜎𝛼𝑘 2 is

[Formula on PDF page 13](../assets/supp_figs/s002-formula-p0013-000.jpg)

where 𝜐̃𝛼= 𝐶+ 𝜐𝛼 and 𝜏̃𝛼 2 = (𝜶𝑘 ′ 𝜶𝑘+ 𝜐𝛼𝜏𝛼 2)/𝜐̃𝛼.

[Formula on PDF page 13](../assets/supp_figs/s002-formula-p0013-002.jpg)

# Algorithm pseudo code

## SBayesRC algorithm

1 Input: GWAS summary statistics, reference LD correlation matrix, functional annotation data

2 Scale the GWAS marginal effect estimate 𝑏𝑗= 𝑠𝑗𝑏𝑗 ∗

3 Construct the low-rank model by performing eigen-decomposition on LD blocks

4 Initialize model parameters

5 for i :=1 to number of iterations do

[Table on PDF page 14](../assets/supp_table/s002-table-p0014-007.csv)

| **6** | **for**j := 1**to**number of SNPs**do** |
| --- | --- |
| **7** | Calculate𝑟𝑗= 𝐐𝑗<br>′𝐰𝑐𝑜𝑟𝑟+ 𝛽𝑗 |
| **8** | Calculate𝐶𝑗= 1 +<br>𝜎𝑒<sup>2</sup><br>𝛾𝑘𝜎𝑔<sup>2</sup><br> for each𝛾𝑘 |
| **9** | Calculate the posterior probabilities of SNP effect distribution memberships and sample𝛿𝑗 |
| **10** | <br>Sample SNP effect𝛽𝑗from its full conditional distribution𝑁(<br>𝑟𝑗<br>𝐶𝑗<br>,<br>𝜎𝜖<sup>2</sup><br>𝐶𝑗<br>~~)~~ |
| **11** | <br>Given the sampled value of𝛽𝑗<br>𝑛𝑒𝑤,adjust𝐰𝑐𝑜𝑟𝑟<br>𝑛𝑒𝑤= 𝐰𝑐𝑜𝑟𝑟<br>𝑜𝑙𝑑+ 𝐐𝑗(𝛽𝑗<br>𝑜𝑙𝑑−𝛽𝑗<br>𝑛𝑒𝑤) |
| **12** | <br>Calculate indicator variables𝐳𝑗given𝛿𝑗 |
| **13** | <br>**end** |
| **14** | <br>**for**k := 2**to**number of mixture distribution components**do** |
| **15** | <br>**for**j := 1**to**number of SNPs that passed the bar for current component**do** |
| **16** | <br>Sample latent variable𝑙𝑗𝑘from a truncated normal distribution given𝑧𝑗𝑘 |
| **17** | <br>**end** |
| **18** | <br>**for**c := 1**to**number of annotations**do** |
| **19** | <br>Sample annotation effect𝛼𝑘𝑐from its full conditional distribution given𝒍𝑘 |
| **20** | <br>**end** |
| **21** | <br>Sample annotation effect variance𝜎𝛼𝑘<br>2from its full conditional distribution given𝜶𝑘 |
| **22** | <br>**end** |
| **23** | <br>Calculate𝐰̂ = 𝐐𝜷and total genetic variance𝜎𝑔<br>2 = 𝐰̂′𝐰̂ |
| **24** | <br>Estimate the per-SNP heritability enrichment for each annotation |
| **25**<br>**26** | <br>Sample residual variance𝜎𝜖<sup>2</sup>from its full conditional distribution for each block<br>**end** |

27 Scale back the posterior mean SNP joint effects to per-allele scale by 𝛽̂𝑗 ∗= 𝑠𝑗𝛽̂𝑗

# 9. Calibrating parameters for the low-rank model

We used simulation to calibrate our low-rank model which requires a specification of two parameters: the minimum width (cM) of a LD block after merging contiguous small quasi- independent LD blocks1, and the minimum proportion (𝜌) of variance in the LD matrix explained by the selected PCs in each LD block. We simulated GWAS data using 1,154,522 SNPs on 328,501 individuals of European ancestry in the UK Biobank7 (UKB) and calculated the prediction accuracy in a hold-out sample of 14,000 individuals. The results showed that the prediction accuracy increased slightly with the LD block width, reaching to a plateau at 4cM (Supplementary Fig. 2). Consequently, we used a minimum block width of 4cM in the subsequent analysis. The other parameter 𝜌 had a greater impact on the prediction accuracy, for which the optimal value would, in principle, depend on the data used for GWAS and LD reference. To determine the best 𝜌 value automatically, we employed a pseudo-validation approach based on the observed GWAS summary statistics and the result of eigen-decomposition on the LD matrix as mentioned below (Supplementary Note 10).

# 10. Tuning for the optimal eigenvalue cut-off

Our low-rank model requires a cut-off value for the minimal proportion (𝜌) of variance explained by the eigenvalues in each LD block. The optimal choice of 𝜌 was determined by a summary-data-based validation approach, following the strategy in Zhang et al8. First, we constructed a set of summary statistics for training and a set for validation, conditional on the observed GWAS summary statistics and the LD reference data. Second, we carried out multiple short runs (150 iterations) of SBayesRC analysis (without annotations) to estimate the SNP joint effects using the training summary statistics and different 𝜌 values (𝜌= [0.9,0.95,0.99,0.995]′ by default). Third, we computed the prediction accuracy using the validation summary statistics. Finally, we used the 𝜌 that gave the highest prediction accuracy in the formal analysis. In contrast to Zhang et al, where the strategy of summary- data-based validation was used to tune the model parameters (e.g., 𝝅), we only used this strategy to find the optimal 𝜌 value and still estimate all model parameters from the data. In addition, in Zhang et al, individual-level genotype data from the reference are required, whereas our approach, as described below, only requires the LD correlation matrix without a need to access to the genotype data.

Construction of pseudo summary statistics for training and validation. The observed GWAS summary statistics can be partitioned into training and validation sets by recognising (Zhao et al)

[Formula on PDF page 16](../assets/supp_figs/s002-formula-p0016-001.jpg)

assuming standardised genotypes, where the subscript 𝑡 and 𝑣 denote the training and validation data sets. Under the assumption of normality and unit phenotypic variance, we have

[Formula on PDF page 16](../assets/supp_figs/s002-formula-p0016-003.jpg)

where 𝜇 is the true SNP marginal effects. The covariance between 𝑏 and 𝑏𝑡 is

[Formula on PDF page 16](../assets/supp_figs/s002-formula-p0016-005.jpg)

According to the property of bivariate normal distribution, the conditional expectation and variance of 𝑏𝑡|𝑏 are

[Formula on PDF page 16](../assets/supp_figs/s002-formula-p0016-007.jpg)

Therefore, the conditional distribution of 𝑏𝑡|𝑏 is

[Formula on PDF page 17](../assets/supp_figs/s002-formula-p0017-001.jpg)

To obtain samples from this multivariate normal distribution efficiently, we make use of the eigen-decomposition results for each LD block. That is,

[Formula on PDF page 17](../assets/supp_figs/s002-formula-p0017-003.jpg)

where 𝑈 and Λ are matrices of eigenvectors and eigenvalues with the maximum cut-off of variance explain (𝜌= 0.995 by default). Let 𝜉 is a vector of standard normal random numbers with the size equal to the number of kept eigenvalues, i.e.,

[Formula on PDF page 17](../assets/supp_figs/s002-formula-p0017-005.jpg)

Then,

[Formula on PDF page 17](../assets/supp_figs/s002-formula-p0017-007.jpg)

The validation data set therefore is

[Formula on PDF page 17](../assets/supp_figs/s002-formula-p0017-009.jpg)

The marginal standard error for 𝑏𝑡 and 𝑏𝑣 is simply √1/𝑛𝑡 and √1/𝑛𝑣, respectively.

Calculation of prediction accuracy based on summary statistics. We compute the prediction accuracy as the correlation of phenotypes and PRS in the validation sample, i.e.,

[Formula on PDF page 17](../assets/supp_figs/s002-formula-p0017-012.jpg)

As shown in Zhao et al9 and Zhang et al10, the covariance term can be written as a function of validation summary statistics,

[Formula on PDF page 17](../assets/supp_figs/s002-formula-p0017-014.jpg)

Besides,

[Formula on PDF page 17](../assets/supp_figs/s002-formula-p0017-016.jpg)

Putting all together, the prediction accuracy of pseudo-validation can be calculated as

[Formula on PDF page 17](../assets/supp_figs/s002-formula-p0017-018.jpg)

In SBayesRC, we start by running multiple chains with different 𝜌 value of 0.995, 0.99, 0.95, and 0.9, for 150 tunning iterations (posterior mean of 𝛽 calculated from the last 50 iterations).

We calculate the pseudo-validation R in each chain. If R>0 and |R / R from 0.995| is larger than 1.25, SBayesRC will switch the 𝜌 to the new value from the default of 0.995. If the largest R is from 𝜌 = 0.9, then we will prompt the user to further expand the grid to 0.8, 0.7, 0.6 or check the QC of the summary data.

# 11. Violation of model assumptions

There are at least two important assumptions implied in the general form of summary-data- based models6. One assumption is that the LD correlation matrix calculated from the reference sample is consistent with that from the GWAS sample, which is violated when the LD reference has a too small sample size (i.e., large sampling variation in LD) or is genetically different from the GWAS sample. Another assumption is that the summary statistics are derived from the same set of individuals for all SNPs, which may not hold when the summary statistics are obtained from a meta-analyses where different SNP genotyping panels, imputation references or quality control (QC) procedures are used in different cohorts. Failure to satisfy these assumptions can result in severe model misspecifications. In SBayesRC (or SBayesRC without annotations), we aim to account for the heterogeneity in both LD and per-SNP sample size by removing those principal components with the smallest eigenvalues in the LD matrix and estimating the residual variance from the data (Methods). We performed genome-wide simulations based on the imputed SNP data in the UKB to assess the robustness of  our method to model misspecifications, in comparison of state-of- the-art methods including LDpred25 and SBayesR.

# 12. Sensitivity analysis in simulation for SBayesRC

For sensitivity analysis, we conducted additional runs of SBayesRC using different mixture distribution scaling factors or the number of mixture components, which deviated from the true values used in the simulation. We observed only negligible changes in the prediction accuracy, indicating that SBayesRC is highly robust to these variations in model specifications (Supplementary Fig. 9 and 10). Moreover, to assess the performance of SBayesRC under an alternative data-generative model, we simulated data where the SNP effect variance was modelled as a weighted sum of components based on functional annotations, akin to a model of S-LDSC11 or MegaPRS8. Even in this scenario, SBayesRC demonstrated superior performance (Supplementary Note 13 and Supplementary Fig. 10).

# 13. Simulation under the S-LDSC/MegaPRS model

We have performed additional simulations where the variance of effect sizes is additively linked to the functional annotations (similar to the LDAK-BayesR-SS or S-LDSC model). The data generative model is:

𝛽𝑗 ~ 𝜋1𝛿0 + 𝜋2𝑁(0,𝑠𝜎𝑗 2/100) + 𝜋3𝑁(0,𝑠𝜎𝑗 2/10) + 𝜋4𝑁(0,𝑠𝜎𝑗 2)

Where 𝑠= 1/( 𝜋2 100 + 𝜋3 10 + 𝜋4),  𝜎𝑗 2 = ∑𝑎𝑗𝑐𝜏𝑐 2 𝑐 with 𝑎𝑗𝑐 being the observed annotation per SNP and 𝜏𝑐 2 being the annotation heritability enrichment parameter from height, and 𝜋1, 𝜋2, 𝜋3, 𝜋4 are set to be 0.998, 1.8910-3, 9.2610-6, and 1.9710-9, respectively. The trait heritability was set to be 0.1 or 0.5. The pattern of prediction accuracy from using 1M or 7M SNPs and with or without annotations in SBayesRC is similar between the two data generative models (SBayesRC model or S-LDSC model for simulation). In both cases, SBayesRC with 7M SNPs and annotations gave the highest prediction accuracy. We noted that overall the prediction accuracy using the S-LDSC model in the simulation was higher than that using the SBayesRC model in the simulation. This may be because, under the S- LDSC model, some causal variants can have a large causal effect, leading to a large discovery power from GWAS, and therefore higher prediction accuracy. In this case, the added value from the annotations became trivial.

# 14. Difference between the LDSC/MegaPRS model and SBayesRC model

S-LDSC12 assumes that each SNP effect has a univariate normal distribution and is not from a mixture model. In this case, it is reasonable to model the SNP effect variance as a weighted sum of components with respect to functional annotations, i.e., 𝛽𝑗 ~ 𝑁(0,𝜎𝑗 2), with 𝜎𝑗 2 = ∑𝑎𝑗𝑐𝜏𝑐 2 𝑐 where 𝑎𝑗𝑐 is the value of annotation c at SNP j and 𝜏𝑐 2 is the heritability enrichment in annotation c. MegaPRS10 is a tool comprising multiple summary-data-based prediction methods, including an infinitesimal model (LDAK-Ridge-SS), a two-normal mixture model (LDAK-Bolt-SS), and a multi-component mixture model (LDAK-BayesR-SS). LDAK- Ridge-SS can be regarded as an equivalent model as S-LDSC. However, in LDAK-BayesR- SS, 𝛽𝑗 ~ 𝜋1𝛿0 + 𝜋2𝑁(0,𝜎𝑗 2/100) + 𝜋3𝑁(0,𝜎𝑗 2/10) + 𝜋4𝑁(0,𝜎𝑗 2), the biological interpretation is not straightforward. For example, 𝜋2 cannot be interpreted as the proportion of SNPs in the small effect size category because whether the effect size is small or large depends on 𝜎𝑗 2 which is annotation dependent. This may potentially affect the identifiability of the mixture membership if annotation-specific heritability enrichment parameters 𝜏𝑐 2 are

estimated jointly with the SNP effects 𝛽𝑗 (instead, a two-step estimation approach is used in the MegaPRS paper, where 𝜏𝑐 2 are estimated by BLD-LDAK model first and then treated as unknown quantities in LDAK-BayesR-SS).

To improve the model interpretability and potentially identifiability and robustness, we assume that

𝛽𝑗 ~ 𝜋𝑗1𝛿0 + 𝜋𝑗2𝑁(0,𝜎𝑔 2/10000) + 𝜋𝑗3𝑁(0,𝜎𝑔 2/1000) + 𝜋𝑗4𝑁(0,𝜎𝑔 2/100) where the mixture distributions are independent of annotations, which represent zero, small, medium and large effect sizes that, in order, explains 0, 0.01%, 0.1% and 1% of the total genetic variance (𝜎𝑔 2). The mixture distribution membership probabilities, 𝜋𝑗1, 𝜋𝑗2, 𝜋𝑗3,𝜋𝑗4, are dependent of annotations such that the interpretation for the annotation effects are straightforward, that is, the higher value of the annotation would increase or decrease the probability of the SNP with an effect belong to a given effect size distribution. Since the model is clearly defined, there is no identifiability problem when estimating SNP effects and annotation effects altogether, which we believe is favourable compared to the two-stage estimation approach.

# 15. Comparison between SBayesRC and MegaPRS

We compared the performance of SBayesRC and MegaPRS (LDAK-BayesR-SS) model using simulations and real data. First, we simulated data based on the SBayesRC model and analysed using the SBayesRC or MegaPRS methods. Second, we simulated data based on the MegaPRS model (or equivalently, the S-LDSC model, when no extra LD weights are modelled) and analysed using the SBayesRC or MegaPRS methods. The details of simulation are described above. We found that SBayesRC gave a higher prediction accuracy than MegaPRS regardless of which data generative model was used in the simulation

(Supplementary Fig. 11). Third, we ran MegaPRS in the 10-fold cross-validation analysis in the UKB of European ancestry, and found that, although outperformed LDpred2 and LDpred- funt, the prediction accuracy was lower than that from SBayesRC (Fig. 3a), consistent with the simulation results. Fourth, we applied MegaPRS in cross-biobank prediction analyses, including training in FinnGen and validation in UKB, and training in the data set from published meta-analysis and validation in Lifelines, across quantitative traits and diseases. Our results showed that SBayesRC had a better predictive performance than MegaPRS, measured by the prediction accuracy relative to LDpred2 (we did not compute the prediction

accuracy relative to the standard SBayesR because of the convergence issue in the standard SBayesR for some of the traits) (Fig. 3b). In particular, SBayesRC had a significant advantage over MegaPRS when using an external LD reference independent of the GWAS sample (Extended Data Fig. 7). Additionally, the advantage of SBayesRC over MegaPRS is observed with different training sample sizes for height and BMI (Fig. 3c). Moreover, our investigation in this study identified a significant interaction between SNP density and annotation information for improving polygenic prediction. We observed this beneficial interactive effect in both within-EUR and cross-ancestry prediction. We note that this is an important result that has not been concluded by the MegaPRS paper, which mainly focused on ~600K directly genotyped SNPs. Last but not least, although MegaPRS is capable of analysing 7M SNPs with annotations, it requires almost 3x larger memory than our method (Table 1).

The superiority of SBayesRC may result from three reasons. First, modelling annotations as a function of 𝜋 may be a better way of incorporating annotation data, as explained above. Second, in SBayesRC, all parameters are estimated coherently in one model, whereas MegaPRS takes heritability enrichment estimates and different sets of 𝜋 values as input and do not consider the estimation variance for these parameters. Third, SBayesRC simultaneously fits all SNPs in the model, but MegaPRS only fits a subset of SNPs that are enriched in per-SNP heritability comparing to a random SNP in the genome. SNPs with depletion in heritability enrichment may still have a nonzero, albeit small, effect on the trait, and completely ignoring them may adversely affect prediction accuracy. Last, SBayesRC better accounted for the sampling variation in LD between the reference and GWAS samples through the low-rank approximation, which is likely to give higher prediction accuracy when using an external LD reference that is independent of the GWAS sample.

16. Other factors affecting accuracy of prediction leveraging functional annotations Here we investigate other factors, besides SNP density, that affect accuracy of prediction leveraging functional annotations, including SNP-based heritability, GWAS sample size, properties of minor allele frequency (MAF) and LD, the number of annotations, and the strategy of analysis.

Stratifying traits based on the SNP-based heritability estimates from SBayesR found that traits with lower SNP-based heritability tended to benefit more from exploiting annotation data on 7M SNPs (regression slope = -15.7, P=0.031; Fig. 6a). When down sampling the UKB data for GWAS in height and BMI, the relative prediction accuracy using 7M SNPs and annotations was higher with a smaller GWAS sample size, while using more SNPs alone required a larger sample size to achieve a higher improvement in prediction accuracy (Fig. 6b). This is expected because including annotations in the model adds more information, whereas including more SNPs in the model alone increases the number of parameters to estimate, consuming more degrees of freedom. Given that most traits have a polygenic architecture, low SNP-based heritability or small sample size means low power in GWAS. Thus, these results suggest that traits with limited GWAS power would benefit more from leveraging annotation data for prediction.

To investigate whether functional annotations provide additional information compared to LD and MAF properties, the relative prediction accuracy for height and BMI was evaluated by fitting various combinations of annotations. We found that the relative prediction accuracy increased with fitting 13 MAF related annotations and had no significant change when adding 4 LD bins, but further increased with additional functional annotations (Fig. 6c). Moreover, when conditional on MAF and LD bins, the improvement was larger with 96 functional annotations compared to 21 core annotations13. These results indicate that functional annotations are more informative than LD and MAF annotations, and using a comprehensive set of functional annotations is superior to using only a few key functional categories.

Lastly, we compared alternative strategies of analysing all common SNPs with annotations. Simultaneous fitting of 7M SNPs in the model is computationally impractical in most MCMC-based methods. One strategy is to perform a stepwise analysis10,14,15, described as below. Step 1, estimation of the impact of functional annotations on SNP effects, which is often quantified by the estimated annotation-specific enrichment in per-SNP heritability using S-LDSC12. Step 2, prioritisation of all SNPs based on their functional annotations and the results from step 1. The final analysis uses a subset of the SNPs that rank from the top in Step 2. To compare our method to such a stepwise strategy, we selected the top 1M SNPs from 7M SNP set based on the results from S-LDSC12, and performed the prediction analysis in height and BMI. For SBayesRC, in which annotations were not assigned, the functionally prioritised 1M SNP set exhibited higher prediction accuracy than the 7M SNPs. However, for

SBayesRC, in which annotations were assigned, the functionally prioritised 1M SNP set was slightly better than the same set of SNPs without re-estimation the annotation effects but was inferior to the 7M SNP set (Fig. 6d). These results suggest that the unified analysis using all 7M SNPs in the model is better than the stepwise analysis in refining the information from annotation data.

# 17. Summary data imputation

We implement the imputation method for summary data from ImpG16 to avoid the heavy re- calculation of the eigen decomposition for the LD matrix if some SNPs are missing from the LD panel. The imputation is based on the Z score, correlation information among missing SNPs and the typed SNPs. The Z score for the missing SNPs can be obtained from

[Formula on PDF page 23](../assets/supp_figs/s002-formula-p0023-003.jpg)

Where zi is the imputed Z score for missing SNPs in the GWAS summary data, 𝐑𝑖𝑡 is the LD correlation matrix among the missing SNPs and typed SNPs,  𝐑𝑡𝑡 is the LD correlation matrix among the typed SNPs.

We converted the 𝐳𝑖 for missing SNPs to marginal effects at 0/1/2 scale (b*) and standard error (𝜎𝑖) by

[Formula on PDF page 23](../assets/supp_figs/s002-formula-p0023-006.jpg)

Where 𝑁𝑖 is the per-SNP sample size (replaced by median per-SNP sample size of known SNPs instead), 𝑓𝑖 is the allele frequency from reference genotype, 𝜎𝑦 is the phenotypic standard derivation (square root of phenotypic variance). The phenotypic variance can be estimated by taking the median value of 2𝑓𝑖(1 −𝑓𝑖)[𝑁𝑖𝜎𝑖 2 + (𝑏𝑖 ∗)2] across SNPs, here 𝑓𝑖 is the allele frequency in the GWAS sample (ref3,4).

# 18. Running settings for the cross-validation in the UKB

SBayesR17 and LDpred25. Only 1M HapMap3 common SNPs were used due to high computational burden. Chromosome-wise banded LD matrices with a window size of 3cM per SNP were calculated from the LD reference sample. As recommended by the authors of LDpred2, LDpred2 was run with the grid of models setting (96 models), and the hold-out sample of 5,991 UKB individuals with genotypes and phenotypes was used to choose the best model for prediction.

C+PT, LDpred-funct18, MegaPRS8, and SBayesRC. Both 1M and 7M common SNP sets were used in these methods. For MegaPRS, the LDAK-BayesR-SS model was used for comparison, as recommended in their paper. For C+PT, a hold-out sample of 5,991 UKB individuals was used as the tunning data, same as in LDpred2. LDpred-funct used the validation sample as the tuning data, which may result in overfitting and inflate the prediction accuracy, so caution is advised. The functional annotation for LDpred-funct, MegaPRS, and SBayesRC was from BaselineLD model v2.219, which contains 96 annotations, including functional genomic annotations, such as coding, promoter, enhancer, or conserved variants and MAF related annotations (10 MAFbins, MAF_Adj_Predicted_Allele_Age, MAF_Adj_ASMC and MAF_Adj_LLD_AFR).

19. Running settings for trans-ancestry prediction

1) Model with summary statistics from EUR only.

SBayesR family. We ran SBayesR17 and SBayesRC using the summary statistics of UKB EUR, and then applied the estimated SNP effects directly to the genotypes of individual of SAS, EAS and AFR ancestries in the UKB.

PolyPred-S. We followed the steps in ref20, where we first used PolyFun + SuSiE for fine- mapping of 7M SNPs with functional annotations from BaseLineLF and LD data from the PolyPred program calculated from the UKB (a step called PolyFun-pred). Then, the mix SNP weights were optimised in 500 tuning samples of the target ancestry using predictors from both Polyfun-pred and SBayesR (trained in EUR). We obtained the PGS from the optimised SNP weights and the genotypes for each target ancestry (SAS, EAS, and AFR) in the UKB.

To ensure robustness and reduce sampling variation in the relative prediction accuracy, we excluded 10 traits with prediction accuracy (R2) from SBayesR less than 0.05 in the cross- validation in EUR and removed one trait (age at menarche) that failed to converge with PolyPred-S. As a result, we retained 17 traits for the trans-ancestry prediction analysis.

2) Model summary statistics from two population together.

PRS-CSx21, SBayesRC-multi, and MegaPRS-multi. We evaluated these methods based on their performance in predicting individuals of EAS and AFR ancestries (target ancestries),

using publicly available GWAS summary statistics from BioBank Japan (BBJ)22 and Population Architecture using Genomics and Epidemiology (PAGE)23 datasets. We focused on 8 common traits between our selected traits and BBJ, and another 8 common traits with PAGE. PRS-CSx requires 500 cases in the target tunning samples, but there were not enough case/control samples for disease traits in the UKB of other ancestries, so the analysis was performed only for continuous traits (Supplementary Table 5 and 6). The 500 hold-out samples from each of the UKB EAS and AFR were used as the tunning sample. We matched the SNPs in the summary data from BBJ, PAGE, and UKB, and removed SNPs with MAF < 0.005 in either population. After QC, 4,906,538 SNPs remained with functional annotations for EAS, of which 1,011,961 SNPs were in the HapMap3 panel, and 6,064,174 SNPs remained for AFR, of which 1,131,955 SNPs were in the HapMap3 panel. We ran PRS-CSx with GWAS summary statistics from UKB EUR and BBJ populations, and LD data from UKB EUR and EAS downloaded from the website (https://github.com/getian107/PRScsx), using the default parameters. Same pipeline was applied to the analysis of UKB EUR and PAGE AFR datasets with LD data from UKB EUR and AFR. After obtaining the SNP weights specific to EUR and the target (EAS or AFR) populations, we calculated the EUR- based and the target-based PGS with genotypes from the UKB target population. Then, we estimated the optimal weights to combine the two sets of PGS using the target tuning samples with phenotypes, as suggested by PRS-CSx. The prediction accuracy was calculated from the optimised PGS and phenotypes in the remaining target validation samples. Following a similar strategy, we extended our method to utilise GWAS data from multiple populations (SBayesRC-multi) and did the same for MegaPRS-multi. Instead of joint modelling, we ran SBayesRC or MegaPRS using summary statistics from UKB EUR and LD from UKB EUR. Then, we ran the methods using summary statistics from BBJ or PAGE with LD from UKB EAS or AFR separately. Finally, the final SNP effects for the target individuals were derived by combining the EUR- and the target-based PGS in the target tuning samples, as described above.

# 20. Reason for using cross-validation in the UKB analysis

The k-fold cross-validation approach has been widely used in the PRS analysis. We reported the mean prediction R2 across 10 folds and believe this is more reliable to the result from a single random sample for the training set with the remaining being the validation set, because the mean value is expected to average out potential ascertainment bias in partitioning training

and validation samples. In addition, cross-validation provides a way to compute the standard error of the prediction accuracy for a trait, which is important when comparing differences in prediction performance between models/scenarios. For example, as shown in Fig. 5 of the main text, the improvement in prediction accuracy due to the use of annotations was significantly higher at 7M imputed SNPs than 1M HapMap3 SNPs for each trait, which can be seen from the standard error obtained from the cross-validation approach.

The reason we used 342K unrelated (genomic relationship cut-off at 0.05) individuals only is that SNPs can capture both direct and indirect genetic effects in the family as well as family- specific environmental effects, which will, if validation samples include relatives of training samples, lead to a higher prediction accuracy than that would be expected in a random sample of the population. Prediction accuracy in an independent random sample remains the most widely accepted criterion to assess the PRS performance. Therefore, we wished to only include the unrelated individuals in the validation set and did not use data from other individuals beyond the 342K unrelated samples of European ancestry.

# 21. Acknowledgements

## Lifelines Cohort Study

The Lifelines Biobank initiative has been made possible by funding from the Dutch Ministry of Health, Welfare and Sport, the Dutch Ministry of Economic Affairs, the University Medical Center Groningen (UMCG the Netherlands), University of Groningen and the Northern Provinces of the Netherlands. The generation and management of GWAS genotype data for the Lifelines Cohort Study is supported by the UMCG Genetics Lifelines Initiative (UGLI). UGLI is partly supported by a Spinoza Grant from NWO, awarded to Cisca Wijmenga. The authors wish to acknowledge the services of the Lifelines Cohort Study, the contributing research centers delivering data to Lifelines, and all the study participants.

## UK Biobank

This study has been conducted using UK Biobank resource under Application Number 12514. UK Biobank was established by the Wellcome Trust medical charity, Medical Research Council, Department of Health, Scottish Government and the Northwest Regional Development Agency. It has also had funding from the Welsh Assembly Government, British Heart Foundation and Diabetes UK.

# FinnGen Study

The FinnGen study is a large-scale genomics initiative that has analyzed over 500,000 Finnish biobank samples and correlated genetic variation with health data to understand disease mechanisms and predispositions. The project is a collaboration between research organisations and biobanks within Finland and international industry partners. We want to acknowledge the participants and investigators of the FinnGen study.

# Supplementary Figures

[Figure on PDF page 28](../assets/supp_figs/s002-figure-p0028-001.jpg)

Supplementary Figure 1 The low-rank model leads to a substantial reduction in dimension. a) The distribution of the number of SNPs per block (mk). b) The distribution of the number of principal components (qk) that collectively explain at least 𝜌 proportion of LD variance in each block (𝜌= 99.5%). c) The distribution of qk/mk at 𝜌= 99.5%.

[Figure on PDF page 29](../assets/supp_figs/s002-figure-p0029-000.jpg)

Supplementary Figure 2 Prediction accuracy of SBayesRC using different minimum values of LD block width and different minimum proportions (𝜌) of variance in the LD matrix in the simulated data with heritability = 0.1 or 0.5. Minimum LD block width = 0 means using the original quasi-independent LD blocks found in the European population (ref1) without merging of small LD blocks. Each box plot shows the spread of data in 10 independent simulations: the line is the middle (median), the box covers the middle half (IQR), the whiskers extend to 1.5 times the IQR, and dots show outliers.

[Figure on PDF page 30](../assets/supp_figs/s002-figure-p0030-000.jpg)

Supplementary Figure 3 Estimation of SNP-based heritability, polygenicity (the proportion of causal variants) and residual variance in SBayesRC without annotation using1M HapMap3 SNPs and different choices of LD reference for a simulated trait with heritability = 0.1 or 0.5. The dashed line in panel a and b indicates the true value in the simulation. The dashed line shows the simulated value. Each box plot shows the spread of data in 10 independent simulations: the line is the middle (median), the box covers the middle half (IQR), the whiskers extend to 1.5 times the IQR, and dots show outliers.

[Figure on PDF page 31](../assets/supp_figs/s002-figure-p0031-000.jpg)

Supplementary Figure 4 Robustness of SBayesRC to unequal per-SNP sample sizes in meta-analysis through simulations with a trait heritability of h²=0.1. While SBayesR only converged in the case of 100% SNP overlap, SBayesRC was able to reach convergence in all scenarios. When the trait heritability is low (h²=0.1), methods lacking tuning information (MegaPRS and SBayesRC) exhibited poorer performance, compared to methods incorporating tuning samples (LDpred2-grid). This observation suggests that methods utilizing tuning samples excel in the case of model misspecification when the GWAS power is low. Each box plot shows the spread of data in 10 independent simulations: the line is the middle (median), the box covers the middle half (IQR), the whiskers extend to 1.5 times the IQR, and dots show outliers.

[Figure on PDF page 32](../assets/supp_figs/s002-figure-p0032-000.jpg)

Supplementary Figure 5 Prediction accuracy of phenotypes using PGS derived from different methods for simulated traits (heritability = 0.1 or 0.5). Each box plot shows the spread of data in 10 independent simulations: the line is the middle (median), the box covers the middle half (IQR), the whiskers extend to 1.5 times the IQR, and dots show outliers.

[Figure on PDF page 33](../assets/supp_figs/s002-figure-p0033-000.jpg)

Supplementary Figure 6 Slope of regression (bias) of phenotypes using PGS derived from different methods and SNP panels using the simulated data. The dashed line indicates the slope of 1. Each box plot shows the spread of data in 10 independent simulations: the line is the middle (median), the box covers the middle half (IQR), the whiskers extend to 1.5 times the IQR, and dots show outliers.

[Figure on PDF page 34](../assets/supp_figs/s002-figure-p0034-000.jpg)

Supplementary Figure 7 Genetic architecture parameter estimation using SBayesRC without annotation or SBayesRC (incorporating annotation data) with different SNP panels for a simulated trait (heritability = 0.1 or 0.5). The dashed line indicates the true value in the simulation. Each box plot shows the spread of data in 10 independent simulations: the line is the middle (median), the box covers the middle half (IQR), the whiskers extend to 1.5 times the IQR, and dots show outliers.

[Figure on PDF page 35](../assets/supp_figs/s002-figure-p0035-000.jpg)

Supplementary Figure 8 The effect of random annotations. a) SBayesRC improved prediction accuracy due to incorporation of annotation data, evidenced by the same analysis using a random annotation as negative control for a simulated trait (heritability = 0.5 or 0.1). SBayesRC_rand is SBayesRC when random numbers sampled from a uniform distribution between 0 and 1 are used as annotation data (a negative control for SBayesRC). Each box plot shows the spread of data in 10 independent simulations: the line is the middle (median), the box covers the middle half (IQR), the whiskers extend to 1.5 times the IQR, and dots show outliers. b) The histogram of estimated annotation effects (alpha) when using random annotations in the simulation (trait heritability h2=0.5 or 0.1). The dashed line indicated the true value of zero (random annotations have no effect on the mixing probabilities of SNP effect distribution). Rows 0-3 indicated the simulated components of mixture distribution for the SNP effects. As expected, the estimated annotation effects were centred at zero in each component. However, when the power is relatively low (h2=0.1), the estimated annotation effects were more dispersed, resulting in a slight decrease in prediction accuracy, as shown in panel a.

[Figure on PDF page 36](../assets/supp_figs/s002-figure-p0036-000.jpg)

Supplementary Figure 9 Prediction accuracy from SBayesRC using a different set of mixture distribution scaling factors (𝜸) than the true values for simulating the data. SimuGamma shows the result with 𝜸 values identical to the true values in the simulation 𝜸 = [0, 0.001, 0.01, 0.1, 1]. AltGamma shows the result with 𝜸= [0, 0.001, 0.005, 0.01, 0.02]. Each box has the result from 10 simulation replicates. Each box plot shows the spread of data in 10 independent simulations: the line is the middle (median), the box covers the middle half (IQR), the whiskers extend to 1.5 times the IQR, and dots show outliers.

[Figure on PDF page 37](../assets/supp_figs/s002-figure-p0037-000.jpg)

Supplementary Figure 10 Prediction accuracy with 4 (gamma: [0, 0.001, 0.01, 0.1]), 5 (gamma: [0, 0.001, 0.01, 0.1, 1]), and 6 (gamma: [0, 0.001, 0.01, 0.1, 0.5, 1] components in simulation and real traits. a) Simulated traits based on 5 components (heritability 0.5 or 0.1); b) Height and type 2 diabetes in the UKB cross-validation.  The difference in prediction accuracy is negligible for both simulated and real traits. Each box plot shows the spread of data in 10 independent simulations: the line is the middle (median), the box covers the middle half (IQR), the whiskers extend to 1.5 times the IQR, and dots show outliers.

[Figure on PDF page 38](../assets/supp_figs/s002-figure-p0038-000.jpg)

Supplementary Figure 11 Prediction accuracy of SBayesRC in comparison to MegaPRS in the simulations where data were generated using either SBayesRC or S-LDSC model (simulated heritability = 0.5 or 0.1). Each box plot shows the spread of data in 10 independent simulations: the line is the middle (median), the box covers the middle half (IQR), the whiskers extend to 1.5 times the IQR, and dots show outliers. See the Supplementary Note for details of simulation based on S-LDSC model.

[Figure on PDF page 39](../assets/supp_figs/s002-figure-p0039-000.jpg)

Supplementary Figure 12 Comparison of per-SNP heritability enrichment in functional categories estimated by SBayesRC and S-LDSC using 1M (panel a) or 7M (panel b) SNPs. The result of each functional category was the mean value over 28 independent UKB traits. The black solid line indicates y=x, the blue solid line indicates the regression line of the data points, the shading is the confident interval of the regression line.

[Figure on PDF page 40](../assets/supp_figs/s002-figure-p0040-000.jpg)

Supplementary Figure 13 Relative SNP-based heritability estimate from different methods (baseline: estimate from SBayesR) for 28 independent traits in UKB unrelated European sample.  The dashed line indicates the relative SNP-based heritability equal to 1 (estimation from the method equals to SBayesR). Each box plot shows the spread of data in 28 independent traits: the line is the middle (median), the box covers the middle half (IQR), the whiskers extend to 1.5 times the IQR, and dots show outliers.

[Figure on PDF page 41](../assets/supp_figs/s002-figure-p0041-000.jpg)

Supplementary Figure 14 Genetic architecture estimates from SBayesRC using 7M common SNPs and annotation data for 28 independent traits in the UKB unrelated European sample. a) The proportion of genetic variance explained in the four non-zero mixture components. b) The proportion of causal variants allocated in the four non-zero mixture components.

[Figure on PDF page 42](../assets/supp_figs/s002-figure-p0042-000.jpg)

Supplementary Figure 15 Comparison of prediction accuracy using LDpred-funct from this analysis to that reported in the LDpred-funct paper for the same trait. a) Comparison of prediction accuracy from our running (mean N=282,019) and that from the LDpred-funct paper (mean N=390,208). Although the prediction accuracies were highly correlated (r=0.975), we found a somewhat lower prediction accuracy in most traits, likely because of the smaller sample size used in this study. b) We found that a larger tuning sample size of 20K consistently gave better result than that of 6K in LDpred-funct. c) The default setting in LDpred-funct is to use the validation sample as tuning (x-axis), which gave slightly better prediction accuracy than using an independent validation sample but is subject to overfitting. The black dashed line indicates y=x, the blue solid line indicates the regression line of the data points, the shading is the confident interval of the regression line.

[Figure on PDF page 43](../assets/supp_figs/s002-figure-p0043-000.jpg)

Supplementary Figure 16 Comparison of prediction accuracy (R2) using PRS-CSx from this analysis to that reported in the PRS-CSx paper for the same traits in EAS population training by summary data from UKB (EUR) and BBJ (EAS). The black dashed line indicates y=x.

[Figure on PDF page 44](../assets/supp_figs/s002-figure-p0044-000.jpg)

Supplementary Figure 17 Comparison of prediction accuracy (R2) using PolyPred-S from this analysis to that reported in the PolyPred paper for the same traits across ancestries. The black dashed line indicates y=x. The prediction accuracies were highly correlated (r = 0.976). The differences may come from 1) Different ways to generate the summary statistics (linear regression/ logistic regression vs. linear mixed model); 2) Differences in training SNP panel (7 million vs. 18 million). We have also discussed with the authors to correct potential issues (https://github.com/omerwe/polyfun/issues/80).

# Reference

1. Berisa, T. & Pickrell, J.K. Approximately independent linkage disequilibrium blocks in human populations. Bioinformatics (Oxford, England) 32, 283-285 (2016).

2. Albert, J.H. & Chib, S. Bayesian-Analysis of Binary and Polychotomous Response Data. Journal of the American Statistical Association 88, 669-679 (1993).

3. Lloyd-Jones, L.R. et al. Improved polygenic prediction by Bayesian multiple regression on summary statistics. Nature Communications 10, 5086 (2019).

4. Yang, J. et al. Conditional and joint multiple-SNP analysis of GWAS summary statistics identifies additional variants influencing complex traits. Nat Genet 44, 369-75, S1-3 (2012).

5. Prive, F., Arbel, J. & Vilhjalmsson, B.J. LDpred2: better, faster, stronger. Bioinformatics (2020).

6. Zhu, X. & Stephens, M. Bayesian Large-Scale Multiple Regression with Summary Statistics from Genome-Wide Association Studies. Ann Appl Stat 11, 1561-1592 (2017).

7. Bycroft, C. et al. The UK Biobank resource with deep phenotyping and genomic data. Nature 562, 203-+ (2018).

8. Zhang, Q., Prive, F., Vilhjalmsson, B. & Speed, D. Improved genetic prediction of complex traits from individual-level data or summary statistics. Nat Commun 12, 4192 (2021).

9. Zhao, Z. et al. PUMAS: fine-tuning polygenic risk scores with GWAS summary statistics. Genome Biol 22, 257 (2021).

10. Zhang, Q.Q., Prive, F., Vilhjalmsson, B. & Speed, D. Improved genetic prediction of complex traits from individual-level data or summary statistics. Nature Communications 12(2021).

11. Finucane, H.K. et al. Partitioning heritability by functional annotation using genome- wide association summary statistics. Nat Genet 47, 1228-35 (2015).

12. Finucane, H.K. et al. Partitioning heritability by functional annotation using genome- wide association summary statistics. Nature Genetics 47, 1228-1235 (2015).

13. Gazal, S., Marquez-Luna, C., Finucane, H.K. & Price, A.L. Reconciling S-LDSC and LDAK functional enrichment estimates. Nature Genetics 51, 1202-1204 (2019).

14. Xiang, R. et al. Quantifying the contribution of sequence variants with regulatory and evolutionary significance to 34 bovine complex traits. Proc Natl Acad Sci U S A 116, 19398-19408 (2019).

15. Maarquez-Luna, C. et al. Incorporating functional priors improves polygenic prediction accuracy in UK Biobank and 23andMe data sets. Nature Communications 12(2021).

16. Pasaniuc, B. et al. Fast and accurate imputation of summary statistics enhances evidence of functional enrichment. Bioinformatics 30, 2906-14 (2014).

17. Lloyd-Jones, L.R. et al. Improved polygenic prediction by Bayesian multiple regression on summary statistics. Nat Commun 10, 5086 (2019).

18. Marquez-Luna, C. et al. Incorporating functional priors improves polygenic prediction accuracy in UK Biobank and 23andMe data sets. Nat Commun 12, 6052 (2021).

19. Gazal, S. et al. Linkage disequilibrium-dependent architecture of human complex traits shows action of negative selection. Nature Genetics 49, 1421-+ (2017).

20. Weissbrod, O. et al. Leveraging fine-mapping and multipopulation training data to improve cross-population polygenic risk scores. Nature Genetics 54, 450-+ (2022).

21. Ruan, Y.F. et al. Improving polygenic prediction in ancestrally diverse populations. Nature Genetics 54, 573-+ (2022).

22. Sakaue, S. et al. A cross-population atlas of genetic associations for 220 human phenotypes. Nature Genetics 53, 1415-+ (2021).

23. Wojcik, G.L. et al. Genetic analyses of diverse populations improves discovery for complex traits. Nature 570, 514-+ (2019).

[PDF page 1](../assets/supp_figs/s003-page-0001.jpg)

[PDF page 2](../assets/supp_figs/s003-page-0002.jpg)

[PDF page 3](../assets/supp_figs/s003-page-0003.jpg)

[Figure on PDF page 1](../assets/supp_figs/s004-figure-p0001-000.jpg)

# Peer Review Information

### Journal: Nature Genetics

Manuscript Title: Leveraging functional genomic annotations and genome coverage to improve polygenic prediction of complex traits within and between ancestries Corresponding author name(s): Dr Jian Zeng ,Dr Zhili Zheng

## Reviewer Comments & Decisions:

Decision Letter, initial version:

1st December 2022

Dear Jian,

Your Analysis "Leveraging functional genomic annotations and genome coverage to improve polygenic prediction of complex traits within and between ancestries" has been seen by three referees. You will see from their comments below that, while they find your work of interest, they have raised several relevant points. We are interested in the possibility of publishing your study in Nature Genetics, but we would like to consider your response to these points in the form of a revised manuscript before we make a final decision on publication.

To guide the scope of the revisions, the editors discuss the referee reports in detail within the team, including with the chief editor, with a view to identifying key priorities that should be addressed in revision, and sometimes overruling referee requests that are deemed beyond the scope of the current study. In this case, we ask that you address all technical queries with suitable clarifications and additional analyses where required and that you extend the benchmarking analyses to include MegaPRS and a broader set of traits. We hope you will find this prioritized set of referee points to be useful when revising your study. Please do not hesitate to get in touch if you would like to discuss these issues further.

We therefore invite you to revise your manuscript taking into account all reviewer and editor comments. Please highlight all changes in the manuscript text file. At this stage we will need you to upload a copy of the manuscript in MS Word .docx or similar editable format.

We are committed to providing a fair and constructive peer-review process. Do not hesitate to contact us if there are specific requests from the reviewers that you believe are technically impossible or unlikely to yield a meaningful outcome.

When revising your manuscript:

1

[Figure on PDF page 2](../assets/supp_figs/s004-figure-p0002-000.jpg)

*1) Include a “Response to referees” document detailing, point-by-point, how you addressed each referee comment. If no action was taken to address a point, you must provide a compelling argument. This response will be sent back to the referees along with the revised manuscript.

*2) If you have not done so already please begin to revise your manuscript so that it conforms to our Analysis format instructions, available <a href="http://www.nature.com/ng/authors/article_types/index.html">here</a>. Refer also to any guidelines provided in this letter.

*3) Include a revised version of any required Reporting Summary:

https://www.nature.com/documents/nr-reporting-summary.pdf It will be available to referees (and, potentially, statisticians) to aid in their evaluation if the manuscript goes back for peer review.

A revised checklist is essential for re-review of the paper.

Please be aware of our <a href="https://www.nature.com/nature-research/editorial-policies/image- integrity">guidelines on digital image standards.</a>

Please use the link below to submit your revised manuscript and related files:

[redacted]

<strong>Note:</strong> This URL links to your confidential home page and associated information about manuscripts you may have submitted, or that you are reviewing for us. If you wish to forward this email to co-authors, please delete the link to your homepage.

We hope to receive your revised manuscript within 8-12 weeks. If you cannot send it within this time, please let us know.

Please do not hesitate to contact me if you have any questions or would like to discuss these revisions further.

Nature Genetics is committed to improving transparency in authorship. As part of our efforts in this direction, we are now requesting that all authors identified as ‘corresponding author’ on published papers create and link their Open Researcher and Contributor Identifier (ORCID) with their account on the Manuscript Tracking System (MTS), prior to acceptance. ORCID helps the scientific community achieve unambiguous attribution of all scholarly contributions. You can create and link your ORCID from the home page of the MTS by clicking on ‘Modify my Springer Nature account’. For more information please visit please visit <a

href="http://www.springernature.com/orcid">www.springernature.com/orcid</a>.

We look forward to seeing the revised manuscript and thank you for the opportunity to review your work.

Sincerely, Kyle

2

[Figure on PDF page 3](../assets/supp_figs/s004-figure-p0003-000.jpg)

Kyle Vogan, PhD Senior Editor Nature Genetics https://orcid.org/0000-0001-9565-9665

Referee expertise:

Referee #1: Genetics, statistical methods, polygenic prediction Referee #2: Genetics, statistical methods, polygenic prediction Referee #3: Genetics, statistical methods, polygenic prediction

Reviewers' Comments:

Reviewer #1: Remarks to the Author:

In this paper, Zheng et al introduced SBayesRC, an extension to SBayesR. Overall, this is a very well written paper, with clear and detail explanation of the analyses and the methodology. The improved computational efficiency, and the ability to perform cross-ancestry PRS analyses without necessitating a tuning sample, is welcoming. I have only some minor comments:

1. One of the main claims of the paper is that there is a significant interaction between SNP density and annotation information on the predictive performance. However, I am unsure if the authors performed a formal statistical test to establish the interactive effect of SNP density and whether annotations were included or not. The p-value cited seems to be the improvement of using 7M imputed SNPs vs 1M HapMap 3 SNPs instead of the interactive effect of SNP density and annotation.

2. It is quite interesting to see that LDpred-func performs worse than LDpred2 in most if not all the analyses presented in the current paper. While I understand that LDpred-func is an extension of LDpred instead of LDpred2, which might partially explain the difference in performance, I still find it surprising how bad it performs despite incorporating the annotation information.

3. For the trans-ancestry analyses, which LD matrix do SBayesR and SBayesRC use for the PRS calculation? Do you match the LD population to the GWAS samples (EUR) or the target samples?

4. In Figure 4, when incorporating more SNPs into the model in EAS samples, the performance of SBayesRC without annotation seems to be worse than SBayesR. Is there any possible explanation to this observation?

5. While trans-ancestry analyses aren’t the focus of the current paper, it is still of interest to see the performance of SBayesRC vs PRS-CSx in African samples, which is known to have the worst portability in PRS analyses. Summary statistics from PAGE might be of use, though this might be something for a future paper.

3

[Figure on PDF page 4](../assets/supp_figs/s004-figure-p0004-000.jpg)

Some minor recommendation:

1. Considering the bottleneck of the current algorithm is due to the eigenvalue decomposition algorithm, a possible optimization for future version of SBayesRC might be the use of the Spectra C++ library, which allows for a quick calculation of eigen value and eigen vector on large sparse matrix.

2. While I can find the R-version of the SBayesRC algorithm on the github page, it does not seem clear to me if the algorithm is implemented in the GCTB software. In the documentation on the GCTB website, while there is an option `--annot`, which I assume will run SBayesRC instead of SBayesR, the documentation stated that “The current version only allows binary annotations…” which seems to contradict to what was stated in the current paper, which stated that SBayesRC can handle continuous annotation. Maybe the authors should update the documentations of GCTB to reflect this change?

3. A minor nitpicks on the coloring scheme: it would be nice if the coloring of each tools are consistent across different figures (e.g. LDpred2, SBayesR, SBayesRC, PolyPred-S).

Reviewer #2:

Remarks to the Author:

The authors present an extension of the well established SBayesR methodology for PRS construction. This method adds functional labels to refine the SNP weights, which should in principle (and as shown here, in practice) improve fine-mapping, and therefore PRS robustness across ancestry groups.

As far as I can tell, SBayesR is used relatively widely and several other PRS prediction tools have developed their own version of functionally informed fine-mapping. It therefore makes sense to see SBayesR receive a similar upgrade. While the motivation and purpose and obviously well described in the literature, there are many useful insights from this paper, in particular the contribution of SNP density and its interaction with functional priors, together with added cross ancestry robustness. The analysis is thorough, exhaustive and rigorous. I cannot see major flaws in the arguments. The open source availability of the code is noted and much appreciated.

Reading the paper, my major interrogation lies in my limited understanding of the intuition behind the ability of the model to learn functional weights from the data. The principle of SBayesR, as far as I understand it, consists of reducing the complex SNP diversity using a low rank transformation that, in effect, collapses groups of variants in high LD into independent variables in the model. The idea behind SNP functional data is of course the fact that even within an LD block, different variants can have very different functional annotations, and that should drive the choice of the variant receiving the higher weight. So I find it surprising that this low rank reduction can still enable the Bayesian machinery to learn about the different weights associated with functional annotations. Obviously it does, as evidenced in Figure 7c, but I would like the authors to help me understand why this training can work.

A second comment - and I appreciate it may just be me - is that I am struggling to interpret performance measured as r^2 for binary traits. These are typically measured using AUC, Harrel's C or (better in my opinion) effect size per SD of the PRS (ideally conditional on age, sex and PCs). If I could encourage the authors to adapt ST3 to show these metrics for binary traits, that would be much

4

[Figure on PDF page 5](../assets/supp_figs/s004-figure-p0005-000.jpg)

# appreciated.

Related to this point of metrics for performance evaluation, the r^2 value associated with the PRS for height is massively affected by the inclusion of sex as a covariate in the model (because sex explains about 50% of the height variance, adding it as a covariate doubles the proportion of the residual variance explained by the PRS). I think this is what is stated at line 736 in the Methods section, but I would make it clear in the main text because, as far as height is concerned, this generates substantial confusion in the literature. I would double check that the statements on line 277 comparing the PRS variance to the theoretical variance explained by SNPs are not comparing oranges and apples (i.e. one includes sex as a covariate and one does not). The large delta in these metrics between BMI and height makes me suspicious.

I would also tone down comments on the convergence issues observed in LDPred2 (line 180). These PRS tools typically require some minimum tuning and optimisation. Clearly, as authors of SBayes-RC, the authors will know how to make the most of the tool. My guess is that the LDPred2 authors (and I am not one of them!) would find a way to reach convergence. Hence, this comparison statement may come across as slightly unfair - though I appreciate that the authors also consider SBayesR, with extensive SBayesRC authorship overlap, so there is no doubt an argument for added robustness here.

I also would like to see the authors discuss the need for cross-validation in the UKB work. This is quite a substantial additional computational work, and the UKB is large enough to set aside a large training set while retaining excellent training sample size, especially for quantitative traits. Could I ask the authors to motivate that choice? Is that simply to extract as much data as possible from UKB or is there a rationale around added stability through that 10 fold procedure? Especially as the authors only use ~ 342K unrelated individuals, there are substantial numbers of EUR ancestry individuals that remain usable, and a minimum relatedness cutoff would yield a very large testing set with less than measurable bias associated with relatedness to training in my experience.

I have a minor interpretation issue with the statement starting at line 361, in the results section. The authors make the case that annotation benefits will be maximised when working with sequence data. This seems contradictory with the fact that the authors see an asymptote in performance when a larger set of ~10M SNPs are used. The contradiction is resolved by arguing that this may be a limit of the imputation accuracy. That may be true but one could also argue in the other direction and say that the asymptote is reached because most causal variants are contained in the 7M set. In any case this is a discussion statement, not a result and I would be cautious with this as the added value of sequence data for PRS construction remains unclear.

Just a minor technicality but my pdf version of Supp Tables only includes ST5. That confused me for a while until I found the remaining table in the excel doc. Something to check...

Vincent Plagnol

Reviewer #3: Remarks to the Author:

This manuscript proposes a method SBayesRC to compute polygenic risk scores (PRS). SBayesRC

5

[Figure on PDF page 6](../assets/supp_figs/s004-figure-p0006-000.jpg)

extends SBayesR to use more SNPs and functional annotations. Simulation and real data analysis revealed that SBayesRC improves the prediction accuracy by leveraging the interaction between SNP density and functional annotation. Overall, I think SBayesRC is a solid method and the idea of using the low-rank model is clever. My main concern is about (1) the choice on how to model functional annotation with effect sizes and (2) lack of comparison with MegaPRS to show the improvement. Below are my comments.

Major:

1. SBayesRC assumes that the probability of distribution membership \pi_jk is related to the functional annotation. Another way to model the functional annotation is to assume that the variance of effect sizes (heritability) for each SNP is additively related to the functional annotation (e.g. S-LDSC https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4626285/ and megaPRS https://www.nature.com/articles/s41467-021-24485-y#Sec8). The authors could discuss why they prefer to use the first approach to model the functional annotation.

2. At the same point, for the simulation scenario incorporating annotation data, the SNP probability of membership was linked with the annotation. It would be helpful to investigate the performance of SBayesRC when the variance of effect sizes is additively linked to the functional annotation.

3. SBayesRC assumes that the scaling factor of five distributions as the mixture components is fixed as \gamma = [0, 0.001, 0.01, 0.1, 1]. In simulation, the authors specified the correct \gamma. I was wondering whether SBayesRC would be robust to the misspecification of \gamma.

4. To my knowledge, SBayesR is not the first method that utilizes the functional annotation and use more SNPs to compute PRS. MegaPRS also uses functional annotation, ~7.5M imputed SNPs (https://www.nature.com/articles/s41467-021-24485-y) and has similar assumptions on effect sizes (multi-component mixture priors). It would be helpful if the authors could compare SBayesRC with MegaPRS in simulations and real data analysis.

5. In my opinion, out-of-sample prediction performance based on external summary statistics is the most important and commonly used evaluation approach for the benchmark of PRS methods. Based on my experience, SBayesR can sometimes have convergence problems when applied to external summary statistics. Currently only 2 traits (height and BMI) were analyzed in the benchmark. It would be more convincing if the authors could demonstrate that SBayesRC outperforms other methods on more traits using external summary statistics.

6. Have the authors considered using AFR instead of EAS summary statistics (e.g. PAGE) to derive PRS for trans-ancestry prediction in AFR populations?

Minor:

1. In Figure 1a, why is Anno3 of "causal variant unobserved" different with Anno3 of "causal variant observed"?

2. Results from PRS-CSx should be included in Figure 4.

3. SBayesRC uses 5 mixture components. I was wondering whether increasing or decreasing the

6

[Figure on PDF page 7](../assets/supp_figs/s004-figure-p0007-000.jpg)

number of components could affect the performance.

4. Tuning parameters of LDpred2 and PRS-CSx should be listed in the method section.

5. In Figure 7c, what does the x-axis of "zero effect" mean? Why do some categories have negative values?

# Author Rebuttal to Initial comments

We would like to express our gratitude for the constructive comments from the three reviewers. In this revision, we have now applied SBayesRC to 50 complex traits covering a diverse range of trait categories and genetic architectures, providing a comprehensive representation of human complex traits. We have extended our analysis to include MegaPRS for method comparison through additional simulation and real data analyses. We have also included more traits for out-of-sample prediction using external GWAS summary statistics. We have improved the robustness of our method by implementing a pseudo-tuning approach, leading to an enhanced performance. Moreover, we evaluated our method for the analysis of samples of African ancestry using PAGE data. Please find below our point-to-point response to the reviewer’s comments in blue.

# Reviewer #1:

# Remarks to the Author:

In this paper, Zheng et al introduced SBayesRC, an extension to SBayesR. Overall, this is a very well written paper, with clear and detail explanation of the analyses and the methodology. The improved computational efficiency, and the ability to perform cross-ancestry PRS analyses without necessitating a tuning sample, is welcoming. I have only some minor comments:

1. One of the main claims of the paper is that there is a significant interaction between SNP density and annotation information on the predictive performance. However, I am unsure if the authors performed a formal statistical test to establish the interactive effect of SNP density and whether annotations were included or not. The p-value cited seems to be the improvement of using 7M imputed SNPs vs 1M HapMap 3 SNPs instead of the interactive effect of SNP density and annotation.

We thank the referee for their positive and constructive comments on our paper. In the original manuscript, we first quantified the improvement in prediction accuracy due to the use of annotation information by calculating the relative prediction accuracy from the full model that includes annotations to the basic model that excludes annotations (𝛿2 = 𝑅𝐹𝑢𝑙𝑙 2 −𝑅𝐵𝑎𝑠𝑖𝑐 2 𝑅𝐵𝑎𝑠𝑖𝑐 2 ) at each SNP density level. Then, we evaluated the interaction between SNP density and annotation information by comparing 𝛿2 between 7M imputed SNPs (𝛿7𝑀 2 ) and 1M HapMap3 SNPs (𝛿1𝑀 2 ). If the benefit of including annotations is

7

[Figure on PDF page 8](../assets/supp_figs/s004-figure-p0008-000.jpg)

independent of SNP density (i.e., no interactive effect between SNP density and annotation information), 𝛿7𝑀 2 is expected to be equal to 𝛿1𝑀 2 (i.e., equal amount of improvement in prediction accuracy no matter 7M or 1M SNPs are used). The original Figure 5 showed the average values of 𝛿7𝑀 2 and 𝛿1𝑀 2 across traits for different data sets, including simulation data sets with different heritability settings and the UKB data sets with different ancestries. We have now improved the clarity by showing the results of 𝛿7𝑀 2 and 𝛿1𝑀 2 in the European ancestry for each of the UKB traits analysed in the revised Figure 5, and those from the other ancestries in new Supplementary Figure 19. It can now be clearly seen from the revised Figure 5 that 𝛿7𝑀 2 was significantly greater than 𝛿1𝑀 2 in all 28 independent traits, mostly with a 2-fold difference or more, indicating a strong interaction between SNP density and annotation information. We further formally tested this interaction effect by fitting the indicator variables for SNP density and annotation data as well as their product to the prediction accuracy for each trait. To account for the variability in prediction accuracy between traits because of trait heritability, the prediction R2 from different scenarios (regarding SNP density level and the use of annotations) for each trait was scaled relative to that using HapMap3 SNPs without annotations. Our test result showed that the interaction effect was highly significant (P value = 6.710-7), in addition to the significant main effects (P value for SNP density = 4.210-4 and P value for annotation information = 1.110-5). The interaction effect was also significant in MegaPRS (PInteraction =1.110-5) and LDpred-funct (PInteraction =0.048) (Revised Figure 3a), suggesting that this is capturing a biological signal independent of the prediction methods. We have included the results in the main text (lines 375-392 in Results, lines 498-530 in Discussion and lines 882-897 in Methods).

2. It is quite interesting to see that LDpred-func performs worse than LDpred2 in most if not all the analyses presented in the current paper. While I understand that LDpred-func is an extension of LDpred instead of LDpred2, which might partially explain the difference in performance, I still find it surprising how bad it performs despite incorporating the annotation information.

We thank the referee for raising this point and have examined the LDpred-funct analysis in more details. In the LDpred-funct paper (Marquez-Luna et al 2021), the authors compared LDpred-funct with LDpred and SBayesR but did not include LDpred2 for comparison. They reported, in the abstract, that LDpred- funct using 6M SNPs with annotations attained a 4.6% relative improvement in average prediction accuracy compared to SBayesR using 1M SNPs. This is generally consistent with the result in our analysis that LDpred-funct using 7M SNPs with annotations on average gave 3.5% higher relative prediction accuracy than the standard SBayesR with 1M SNPs (in our SBayesR analysis the 3cM banded matrices was used, same as in LDpred2, which is slightly superior to the shrunk matrices used in the analysis of Marquez-Luna et al). Our investigations show that the superiority of LDpred-funct arises from the combination of using high-density SNPs and annotation data. However, the way LDpred-funct models the data is suboptimal. This can be seen from the result that, when using 1M SNPs with annotations, LDpred-funct is worse than SBayesRC and that, when using 1M SNPs without annotations, LDpred-funct is worse than either SBayesR or LDpred2 on average. Our explanation is that unlike LDpred2 and SBayesR where SNP effects are assumed to have a mixture distribution, which has been shown to be a better model for the genetic architecture for complex traits in the literature (Moser et al 2015; Lolyd-Jones

8

[Figure on PDF page 9](../assets/supp_figs/s004-figure-p0009-000.jpg)

et al 2019; Zhang et al 2018), LDpred-funct fits an infinitesimal model first and then reweighs the SNP effects by groups to approximate the sparse assumption. This two-stage weighting strategy is only an approximation of the mixture model approach, thus unlikely to surpass it.

3. For the trans-ancestry analyses, which LD matrix do SBayesR and SBayesRC use for the PRS calculation? Do you match the LD population to the GWAS samples (EUR) or the target samples?

We used the LD matrix from a random sample of 20K unrelated individuals of EUR ancestry in the UKB, when GWAS summary statistics from the EUR samples only were used for training the model for trans- ancestry prediction. In the analysis that combined data from the EUR sample and a non-EUR sample of the same ancestry with the target population, we ran SBayesRC in each sample separately using an ancestry-matched LD reference in the UKB. The principle is to use a LD reference that matches the GWAS sample in ancestry rather than the target sample. We have clarified this in the revised manuscript (lines 868-869 and 876-878).

4. In Figure 4, when incorporating more SNPs into the model in EAS samples, the performance of SBayesRC without annotation seems to be worse than SBayesR. Is there any possible explanation to this observation?

In the trans-ancestry prediction in EAS samples, the average prediction accuracy across traits was 0.058 from SBayesRC using 1M SNPs without annotations, which is equivalent to the standard SBayesR with the only difference in the way of regularization of LD matrix (a low-rank transformation is used in SBayesRC while a shrunk matrix is used in SBayesR). The average prediction accuracy from SBayesRC using 7M SNPs without annotations was also 0.058. While using 7M SNPs was not better in this case, the use of annotations or the combination of 7M SNPs and annotations increased the mean prediction accuracy to 0.062 and 0.065, respectively. This result suggests that annotations provide more information than high density SNPs for trans-ancestry prediction. This can possibly be explained by the combination of shared causal variants and LD differences between EUR and EAS samples. While including high- density SNPs would in principle help to select the causal variants in the model, the use of more SNPs alone may not be advantageous because there are more parameters to estimate from the data. A larger sample size is required to better estimate the variant effects, which is to some extend achieved using functional annotations. A related discussion on the added value of annotation data to the high-density SNP panel has been included in the revised manuscript (lines 508-516).

5. While trans-ancestry analyses aren’t the focus of the current paper, it is still of interest to see the performance of SBayesRC vs PRS-CSx in African samples, which is known to have the worst portability in PRS analyses. Summary statistics from PAGE might be of use, though this might be something for a future paper.

9

[Figure on PDF page 10](../assets/supp_figs/s004-figure-p0010-000.jpg)

We thank the reviewer for the suggestion and agree that it is of interest to compare SBayesRC vs PRS- CSx using PAGE summary statistics from mixed African samples. In the revised manuscript, we have included the analysis of 8 traits from the PAGE data set that were in common with those in the UKB data set of African ancestries. Similar to the analysis for EAS ancestry, we ran SBayesRC using UKB EUR data set only and SBayesRC-multi which combines data from both UKB EUR samples and PAGE samples, and compared to the performance of PRS-CSx. In SBayesRC-multi, we first ran SBayesRC in UKB EUR data set and PAGE data set separately and then used a tuning sample of 500 individuals of AFR ancestry in the UKB to generate African-specific SNP effect estimates. Likewise, we ran PRS-CSx using the same data with only UKB EUR data set for training or with UKB EUR and PAGE AFR data sets analysed jointly for training (with a tuning step). The prediction accuracy was calculated in the hold- out UKB AFR samples independent of the 500 tuning samples. As expected, in both SBayesRC and PRS- CSx, using both EUR and PAGE data sets for training was superior to using EUR data set only. However, SBayesRC with annotations using EUR data set only has readily outperformed PRS-CSx with both EUR and PAGE data as input, regardless of 1M or 7M SNPs used in SBayesRC (PRS-CSx cannot use 7M SNPs due to computational constraint). When SBayesRC-multi was used, with 7M SNPs, annotations, and AFR data from PAGE, the difference to PRS-CSx increased to 40.9% ( 𝑅SBayesRC 2 −𝑅PRS−CSx 2 𝑅PRS−CSx 2 ) on

average across traits, suggesting that information from annotations at dense SNPs can outweigh that from the summary statistics from the target population. These results are consistent with the observations from the trans-ancestry prediction for EAS (Figure 4c). We have included this new result in the revised Figure 4d, lines 354-359 in Results and lines 853-880 in Methods of the revised manuscript.

Some minor recommendation:

1. Considering the bottleneck of the current algorithm is due to the eigenvalue decomposition algorithm, a possible optimization for future version of SBayesRC might be the use of the Spectra C++ library, which allows for a quick calculation of eigen value and eigen vector on large sparse matrix.

We thank the reviewer for this suggestion. We found that Spectra C++ library is very efficient to generate a small number of top PCs but is not faster than Eigen C++ library when generating all eigenvalues and eigenvectors for a matrix, which is required in our method. We expect that general users would mostly likely only need to use the matrices provided on our website. If they need to perform eigen decomposition because the GWAS data is genetically different from our LD reference (unrelated UKB samples of European ancestry), the computation can be done in parallel between LD blocks and only needs to be run once for different traits. We will update the software when more efficient libraries become available in the future.

10

[Figure on PDF page 11](../assets/supp_figs/s004-figure-p0011-000.jpg)

2. While I can find the R-version of the SBayesRC algorithm on the github page, it does not seem clear to me if the algorithm is implemented in the GCTB software. In the documentation on the GCTB website, while there is an option `--annot`, which I assume will run SBayesRC instead of SBayesR, the documentation stated that “The current version only allows binary annotations…” which seems to contradict to what was stated in the current paper, which stated that SBayesRC can handle continuous annotation. Maybe the authors should update the documentations of GCTB to reflect this change?

We have updated the GCTB software and the website to allow the use of SBayesRC with both quantitative and categorical annotations. The tutorial for SBayesRC can be found here: https://cnsgenomics.com/software/gctb/#Tutorial

3. A minor nitpicks on the coloring scheme: it would be nice if the coloring of each tools are consistent across different figures (e.g. LDpred2, SBayesR, SBayesRC, PolyPred-S).

We agree and have now used the same colour for each method across figures as possible as we can in the revised manuscript.

# Reviewer #2:

Remarks to the Author:

The authors present an extension of the well established SBayesR methodology for PRS construction. This method adds functional labels to refine the SNP weights, which should in principle (and as shown here, in practice) improve fine-mapping, and therefore PRS robustness across ancestry groups.

As far as I can tell, SBayesR is used relatively widely and several other PRS prediction tools have developed their own version of functionally informed fine-mapping. It therefore makes sense to see SBayesR receive a similar upgrade. While the motivation and purpose and obviously well described in the literature, there are many useful insights from this paper, in particular the contribution of SNP density and its interaction with functional priors, together with added cross ancestry robustness. The analysis is thorough, exhaustive and rigorous. I cannot see major flaws in the arguments. The open source availability of the code is noted and much appreciated.

Reading the paper, my major interrogation lies in my limited understanding of the intuition behind the ability of the model to learn functional weights from the data. The principle of SBayesR, as far as I understand it, consists of reducing the complex SNP diversity using a low rank transformation that, in effect, collapses groups of variants in high LD into independent variables in the model. The idea behind

11

[Figure on PDF page 12](../assets/supp_figs/s004-figure-p0012-000.jpg)

SNP functional data is of course the fact that even within an LD block, different variants can have very different functional annotations, and that should drive the choice of the variant receiving the higher weight. So I find it surprising that this low rank reduction can still enable the Bayesian machinery to learn about the different weights associated with functional annotations. Obviously it does, as evidenced in Figure 7c, but I would like the authors to help me understand why this training can work.

We thank the reviewer for the positive remarks and the comment on clarification. The reason why the Bayesian learning about functional annotations can still work in the low-rank model is, in brief, that the low rank approximation still captures >99% of the variance. However, it is expected that with a lower eigenvalue threshold (e.g., 50%), the performance would be compromised. A more detailed explanation is described as below.

The low-rank model is derived from the standard summary-data-based model, where m SNP marginal effects (b) are fitted with m SNP joint effects (𝜷):

[Formula on PDF page 12](../assets/supp_figs/s004-formula-p0012-004.jpg)

with R being a mm matrix and 𝜺 being mutually correlated with a variance-covariance matrix proportional to R. In each LD block, we perform eigen-decomposition on R such that

[Formula on PDF page 12](../assets/supp_figs/s004-formula-p0012-006.jpg)

where U and 𝚲 are matrices of eigenvectors and eigenvalues, respectively. The low-rank model is constructed such that the dimension of observed data (b and R) is reduced but the dimension of parameters (𝜷) remains. In essence, it fits q observables with m SNP joint effects, where q<<m and the observables are correlated only through SNP joint effects but not residuals:

[Formula on PDF page 12](../assets/supp_figs/s004-formula-p0012-008.jpg)

with 𝐰 being a q1 vector and 𝐐 being a qm matrix. As shown in our simulation and real data analyses, the low-rank model approximates the standard model with high accuracy, when the choice of q is well calibrated, and has considerable improvement in computational efficiency and robustness. The functional annotations are incorporated into the prior distribution of 𝛽𝑗:

[Formula on PDF page 12](../assets/supp_figs/s004-formula-p0012-010.jpg)

with 𝐀𝑗 being the observed annotation data matrix for SNP j and 𝜶𝑘 being the vector of unknown annotation effects estimated from the data. In this model, functional annotations describe the prior distribution of SNP joint effects, thereby contributing to the posterior estimation of SNP weights. It is a

12

[Figure on PDF page 13](../assets/supp_figs/s004-figure-p0013-000.jpg)

hierarchical Bayesian learning process for 𝜶𝑘 because 𝜶𝑘 connect to the data (w and Q) only through 𝜷, which means that 𝜶𝑘 can be estimated in either the standard model (1) or the low-rank model (3) since both models have 𝜷 as parameters. Note that an alternative reduction is to reduce the dimension of parameter space, that is, from Eq (2) we can have

𝐛= 𝐔𝜷∗+ 𝜺

where U is a mq matrix and 𝜷∗= 𝚲𝐔′𝜷 becomes a q1 vector that captures the principal component effects. In this case, the Bayesian machinery to learn about the different weights associated with functional annotations would not work because each element of 𝜷∗ is not the SNP joint effect itself but a linear combination of SNP joint effects. We have included this explanation in the Supplementary Note and mentioned at lines 156-158 in the revised manuscript.

A second comment – and I appreciate it may just be me – is that I am struggling to interpret performance measured as r^2 for binary traits. These are typically measured using AUC, Harrel’s C or (better in my opinion) effect size per SD of the PRS (ideally conditional on age, sex and PCs). If I could encourage the authors to adapt ST3 to show these metrics for binary traits, that would be much appreciated.

We thank the referee for this question and for the suggestion. In the original manuscript, we used pseudo R2 from the logistic regression that corrected for the covariates, including age, sex and PCs, to measure the prediction accuracy for binary traits. Unlike in case-control studies, the binary traits in this study were measured in the volunteered participants of UK Biobank, a sample from the general population. Additionally, we used relative prediction accuracy for methods comparison ( 𝑅𝐹𝑢𝑙𝑙 2 −𝑅𝐵𝑎𝑠𝑖𝑐 2 𝑅𝐵𝑎𝑠𝑖𝑐 2 ), where the effect of scale is cancelled so that the R2 for quantitative traits and pseudo R2 for binary traits are comparable. In the revised manuscript, we also calculated AUC and odds ratio per standard deviation of the PRS in the logistic regression conditional on the covariates, including age, sex and PCs, and reported these results in the revised Supplementary Table 3. Our understanding of Harrel’s C-index is that it is commonly used to evaluate model performance in survival analysis but would be identical to AUC for binary data without time-to-disease measurements. In general, both AUC and odds ratio statistics for measuring prediction accuracy in diseases gave consistent results as shown by the pseudo R2. We have described in the main text at lines 829-833.

Related to this point of metrics for performance evaluation, the r^2 value associated with the PRS for height is massively affected by the inclusion of sex as a covariate in the model (because sex explains about 50% of the height variance, adding it as a covariate doubles the proportion of the residual variance explained by the PRS). I think this is what is stated at line 736 in the Methods section, but I would make it clear in the main text because, as far as height is concerned, this generates substantial confusion in the literature. I would double check that the statements on line 277 comparing the PRS variance to the theoretical variance explained by SNPs are not comparing oranges and apples (i.e. one includes sex as a

13

[Figure on PDF page 14](../assets/supp_figs/s004-figure-p0014-000.jpg)

covariate and one does not). The large delta in these metrics between BMI and height makes me suspicious.

We confirmed that both prediction R2 and SNP-based heritability estimates are based on data that have removed the mean and variance differences in sex by rank-based inverse-normal transformation of data within each sex group. The effects of age and 10 PCs were further removed from the GWAS summary data by fitting them as covariates in the GWAS model, and removed from the prediction evaluation by calculating an incremental R2 of PRS through comparing the full model to the basic model that included these covariates. We have described these procedures in the main text at lines 743-745, 796-799, 825-826.

I would also tone down comments on the convergence issues observed in LDPred2 (line 180). These PRS tools typically require some minimum tuning and optimisation. Clearly, as authors of SBayes-RC, the authors will know how to make the most of the tool. My guess is that the LDPred2 authors (and I am not one of them!) would find a way to reach convergence. Hence, this comparison statement may come across as slightly unfair - though I appreciate that the authors also consider SBayesR, with extensive SBayesRC authorship overlap, so there is no doubt an argument for added robustness here.

We agree with the reviewer and have toned down the statement about LDpred2. Our revised manuscript now has the following statement (lines 187-188 “In an extreme case where African ancestry individuals were used to estimate LD correlations, ~70% prediction accuracy was preserved in SBayesRC, whereas both SBayesR and LDpred2 (under default settings) were unable to reach to convergence.”

I also would like to see the authors discuss the need for cross-validation in the UKB work. This is quite a substantial additional computational work, and the UKB is large enough to set aside a large training set while retaining excellent training sample size, especially for quantitative traits. Could I ask the authors to motivate that choice? Is that simply to extract as much data as possible from UKB or is there a rationale around added stability through that 10 fold procedure? Especially as the authors only use ~ 342K unrelated individuals, there are substantial numbers of EUR ancestry individuals that remain usable, and a minimum relatedness cutoff would yield a very large testing set with less than measurable bias associated with relatedness to training in my experience.

The k-fold cross-validation approach has been widely used in the PRS analysis. We reported the mean prediction R2 across 10 folds and believe this is more reliable to the result from a single random sample for the training set with the remaining being the validation set, because the mean value is expected to average out potential ascertainment bias in partitioning training and validation samples. In addition, cross- validation provides a way to compute the standard error of the prediction accuracy for a trait, which is important when comparing differences in prediction performance between models/scenarios. For example, as shown in the revised Figure 5, the improvement in prediction accuracy due to the use of

14

[Figure on PDF page 15](../assets/supp_figs/s004-figure-p0015-000.jpg)

annotations was significantly higher at 7M imputed SNPs than 1M HapMap3 SNPs for each trait, which can be seen from the standard error obtained from the cross-validation approach.

The reason we used 342K unrelated (genomic relationship cut-off at 0.05) individuals only is that SNPs can capture both direct and indirect genetic effects in the family as well as family-specific environmental effects, which will, if validation samples include relatives of training samples, lead to a higher prediction accuracy than that would be expected in a random sample of the population. Prediction accuracy in an independent random sample remains the most widely accepted criterion to assess the PRS performance. Therefore, we wished to only include the unrelated individuals in the validation set and did not use data from other individuals beyond the 342K unrelated samples of European ancestry.

We have included this discussion in the Supplementary Note.

I have a minor interpretation issue with the statement starting at line 361, in the results section. The authors make the case that annotation benefits will be maximised when working with sequence data. This seems contradictory with the fact that the authors see an asymptote in performance when a larger set of ~10M SNPs are used. The contradiction is resolved by arguing that this may be a limit of the imputation accuracy. That may be true but one could also argue in the other direction and say that the asymptote is reached because most causal variants are contained in the 7M set. In any case this is a discussion statement, not a result and I would be cautious with this as the added value of sequence data for PRS construction remains unclear.

We agree with the reviewer that this statement needs to be treated with caution. We have removed it from Results section and discussed this issue in the Discussion section (lines 518-530) with the following text.

“In the real data analysis, a significant improvement was observed from 1M to 7M imputed SNPs with annotations, but no further difference was observed with 10M imputed SNPs (Supplementary Fig. 20). This plateau in prediction performance could be attributed to the saturation of SNP tagging on the common causal variants by the 7M set or due to limitations in imputation accuracy on common SNPs or sample size of discovery GWAS, which is associated with the impact of MAF. This hypothesis can be tested when whole-genome sequence data for the full release of UKB samples becomes available. A recent study62 showed that 91% of rare variants identified using whole-exome sequence data in the UKB are independent of common variant signals. Furthermore, the imputation accuracy decreases with decreasing MAF63, and the estimation variance of variant effects increases with MAF given a fixed sample size. Therefore, it is expected that using variants at sequence level, along with additional information from functional annotations, will provide added value for maximizing prediction accuracy.”

15

[Figure on PDF page 16](../assets/supp_figs/s004-figure-p0016-000.jpg)

Just a minor technicality but my pdf version of Supp Tables only includes ST5. That confused me for a while until I found the remaining table in the excel doc. Something to check...

We thank the reviewer for a careful review. We have ensured all supplementary tables are shown correctly.

# Vincent Plagnol

# Reviewer #3:

Remarks to the Author:

This manuscript proposes a method SBayesRC to compute polygenic risk scores (PRS). SBayesRC extends SBayesR to use more SNPs and functional annotations. Simulation and real data analysis revealed that SBayesRC improves the prediction accuracy by leveraging the interaction between SNP density and functional annotation. Overall, I think SBayesRC is a solid method and the idea of using the low-rank model is clever. My main concern is about (1) the choice on how to model functional annotation with effect sizes and (2) lack of comparison with MegaPRS to show the improvement. Below are my comments.

We thank the reviewer for the positive remarks and constructive comments, which have helped us improve our method.

# Major:

1. SBayesRC assumes that the probability of distribution membership \pi_jk is related to the functional annotation. Another way to model the functional annotation is to assume that the variance of effect sizes (heritability) for each SNP is additively related to the functional annotation (e.g. S- LDSC https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4626285/ and

megaPRS https://www.nature.com/articles/s41467-021-24485-y#Sec8). The authors could discuss why they prefer to use the first approach to model the functional annotation.

We chose to model the functional annotation as a function of the probability of distribution membership because this model is straightforward to interpret, especially in the context of a multi-component mixture model, as explained below.

16

[Figure on PDF page 17](../assets/supp_figs/s004-figure-p0017-000.jpg)

S-LDSC assumes that each SNP effect has a univariate normal distribution and is not from a mixture model. In this case, it makes perfect sense to model the SNP effect variance as a weighted sum of components with respect to functional annotations, i.e., 𝛽𝑗 ~ 𝑁(0, 𝜎𝑗 2), with 𝜎𝑗 2 = ∑𝑎𝑗𝑐𝜏𝑐2 𝑐 where 𝑎𝑗𝑐 is the value of annotation c at SNP j and 𝜏𝑐2 is the heritability enrichment in annotation c. MegaPRS is a tool comprising multiple summary-data-based prediction methods, including an infinitesimal model (LDAK- Ridge-SS), a two-normal mixture model (LDAK-Bolt-SS), and a multi-component mixture model (LDAK-BayesR-SS). LDAK-Ridge-SS can be regarded as an equivalent model as S-LDSC. However, in LDAK-BayesR-SS, 𝛽𝑗 ~ 𝜋1𝛿0 + 𝜋2𝑁(0, 𝜎𝑗 2/100) + 𝜋3𝑁(0, 𝜎𝑗 2/10) + 𝜋4𝑁(0, 𝜎𝑗 2), the biological interpretation is not straightforward. For example, 𝜋2 cannot be interpreted as the proportion of SNPs in the small effect size category because whether the effect size is small or large depends on 𝜎𝑗 2 which is annotation dependent. This may potentially affect the identifiability of the mixture membership if annotation-specific heritability enrichment parameters 𝜏𝑐2 are estimated jointly with the SNP effects 𝛽𝑗 (instead, a two-step estimation approach is used in the MegaPRS paper, where 𝜏𝑐2 are estimated by BLD- LDAK model first and then treated as unknown quantities in LDAK-BayesR-SS).

To improve the model interpretability and potentially identifiability and robustness, we assume that

𝛽𝑗 ~ 𝜋𝑗1𝛿0 + 𝜋𝑗2𝑁(0, 𝜎𝑔2/10000) + 𝜋𝑗3𝑁(0, 𝜎𝑔2/1000) + 𝜋𝑗4𝑁(0, 𝜎𝑔2/100)

where the mixture distributions are independent of annotations, which represent zero, small, medium and large effect sizes that, in order, explains 0, 0.01%, 0.1% and 1% of the total genetic variance (𝜎𝑔2). The mixture distribution membership probabilities, 𝜋𝑗1, 𝜋𝑗2, 𝜋𝑗3, 𝜋𝑗4, are dependent of annotations such that the interpretation for the annotation effects are straightforward, that is, the higher value of the annotation would increase or decrease the probability of the SNP with an effect belong to a given effect size distribution. Since the model is clearly defined, there is no identifiability problem when estimating SNP effects and annotation effects altogether, which we believe is favourable compared to the two-stage estimation approach.

From the simulation and real data analysis, SBayesRC gives higher prediction accuracy than MegaPRS (Fig. 3b and Supplementary Fig. 14 in the revised manuscript), supporting that the first approach is likely a better way of modelling functional annotations than the second approach. We have included this discussion in the Supplementary Note.

2. At the same point, for the simulation scenario incorporating annotation data, the SNP probability of membership was linked with the annotation. It would be helpful to investigate the performance of SBayesRC when the variance of effect sizes is additively linked to the functional annotation.

17

[Figure on PDF page 18](../assets/supp_figs/s004-figure-p0018-000.jpg)

We have performed additional simulations where the variance of effect sizes is additively linked to the functional annotations (similar to the LDAK-BayesR-SS or S-LDSC model). The data generative model is:

[Formula on PDF page 18](../assets/supp_figs/s004-formula-p0018-002.jpg)

where 𝜎𝑗 2 = ∑𝑎𝑗𝑐𝜏𝑐2 𝑐 with 𝑎𝑗𝑐 being the observed annotation per SNP and 𝜏𝑐2 being the annotation heritability enrichment parameter for height, and 𝜋1, 𝜋2, 𝜋3, 𝜋4 are set to be 0.998, 1.89e-3, 9.26e-6, and 1.97e-9, respectively. The trait heritability was set to be 0.1 or 0.5. The pattern of prediction accuracy from using 1M or 7M SNPs and with or without annotations in SBayesRC is similar between the two data generative models (SBayesRC model or S-LDSC model for simulation). In both cases, SBayesRC with 7M SNPs and annotations gave the highest prediction accuracy. We noted that overall the prediction accuracy using the S-LDSC model in the simulation was higher than that using the SBayesRC model in the simulation. This may be because, under the S-LDSC model, some causal variants can have a very large causal effect, leading to a large discovery power from GWAS, and therefore higher prediction accuracy. In this case, the added value from the annotations became trivial.

We compared the performance of SBayesRC and MegaPRS (LDAK-BayesR-SS) model and found that regardless of which data generative model was used, SBayesRC always gave a higher prediction accuracy than MegaPRS. The superiority of SBayesRC may result from three reasons. First, modelling annotations as a function of pi values may be a better way of incorporating annotation data, as explained above. Second, in SBayesRC, all parameters are estimated coherently in one model, whereas MegaPRS takes heritability enrichment estimates and different sets of pi values as input and do not consider the estimation variance for these parameters. Third, SBayesRC simultaneously fits all SNPs in the model, but MegaPRS only fits a subset of SNPs that are enriched in per-SNP heritability comparing to a random SNP in the genome. SNPs with depletion in heritability enrichment may still have a nonzero, albeit small, effect on the trait, and completely ignoring them may adversely affect prediction accuracy.

We have included this result in Supplementary Figure 14 and in the main text at lines 230-234.

3. SBayesRC assumes that the scaling factor of five distributions as the mixture components is fixed as \gamma = [0, 0.001, 0.01, 0.1, 1]. In simulation, the authors specified the correct \gamma. I was wondering whether SBayesRC would be robust to the misspecification of \gamma.

For the simulated data, we compared the SBayesRC analysis with the correct gamma values used in the simulation, i.e., gamma = [0, 0.001, 0.01, 0.1, 1], to the analysis with a very different set of gamma values, gamma = [0, 0.001, 0.005, 0.01, 0.02]. The result showed that the difference in prediction accuracy is negligible, suggesting that SBayesRC is robust to the misspecification of the gamma values

18

[Figure on PDF page 19](../assets/supp_figs/s004-figure-p0019-000.jpg)

(Supplementary Figure 12).  We have included this in main text lines 227-230, and supplementary Figure 12.

4. To my knowledge, SBayesR is not the first method that utilizes the functional annotation and use more SNPs to compute PRS. MegaPRS also uses functional annotation, ~7.5M imputed SNPs

(https://www.nature.com/articles/s41467-021-24485-y) and has similar assumptions on effect sizes (multi-component mixture priors). It would be helpful if the authors could compare SBayesRC with MegaPRS in simulations and real data analysis.

We thank the reviewer for raising the point that MegaPRS is also capable of analysing 7M SNPs with annotations so we should compare the two methods in simulations and real data analyses. To investigate this, we have done a set of additional analyses, using MegaPRS, in particular, the LDAK-BayesR-SS model (multi-component mixture prior), with 7M SNPs and functional annotations. First, we simulated data based on the SBayesRC model and analysed using the SBayesRC or MegaPRS methods. Second, we simulated data based on the MegaPRS model (or equivalently, the LDSC model, when no extra LD weights are modelled) and analysed using the SBayesRC or MegaPRS methods. The details of simulation are described in our response to the reviewer’s comment #2. We found that SBayesRC gave a higher prediction accuracy than MegaPRS regardless of which data generative model was used in the simulation (new Supplementary Figure 14). Third, we ran MegaPRS in the 10-fold cross-validation analysis in the UKB of European ancestry, and found that, although outperformed LDpred2 and LDpred-funt, the prediction accuracy was lower than that from SBayesRC (revised Fig. 3a), consistent with the simulation results. Furthermore, we applied MegaPRS in cross-biobank prediction analyses, including training in FinnGen and validation in UKB, and training in the data set from published meta-analysis and validation in Lifelines, across quantitative traits and diseases. Our results showed that SBayesRC had a better predictive performance than MegaPRS, measured by the prediction accuracy relative to LDpred2 (we did not compute the prediction accuracy relative to the standard SBayesR because of the convergence issue in the standard SBayesR for some of the traits) (revised Fig. 3b). Additionally, the advantage of SBayesRC over MegaPRS is observed with different training sample sizes for height and BMI (revised Fig. 3c). Moreover, our investigation in this study identified a significant interaction between SNP density and annotation information for improving polygenic prediction. We observed this beneficial interactive effect in both within-EUR and cross-ancestry prediction. We note that this is an important result that has not been concluded by the MegaPRS paper, which mainly focused on ~600K directly genotyped SNPs. Last but not least, although MegaPRS is capable of analysing 7M SNPs with annotations, it requires almost 3x larger memory than our method (revised Table 2).

We have included these new results in Fig. 2c, 3, Supplementary Fig. 14, the Supplementary Note, and the Results section in the revised manuscript at lines 214-217 and 267-271, Methods section at lines 812- 820.

19

[Figure on PDF page 20](../assets/supp_figs/s004-figure-p0020-000.jpg)

5. In my opinion, out-of-sample prediction performance based on external summary statistics is the most important and commonly used evaluation approach for the benchmark of PRS methods. Based on my experience, SBayesR can sometimes have convergence problems when applied to external summary statistics. Currently only 2 traits (height and BMI) were analyzed in the benchmark. It would be more convincing if the authors could demonstrate that SBayesRC outperforms other methods on more traits using external summary statistics.

We thank the reviewer for the comment, which has helped us to identify a potential problem of our method and has led to a methodological improvement.

We aimed to run SBayesRC in more traits using external summary statistics. However, the most recently published GWAS for complex traits are predominantly based on the UKB data or have included UKB as part of the meta-analysis. Therefore, the number of applicable traits is limited to the data availability in Lifelines, our independent validation cohort. We found 2 more traits that have a large GWAS sample size and a decent validation sample size in Lifelines, resulting in a total of 4 traits: height (GWAS data from Yengo et al; n_GWAS=704,823; n_Lifelines=11,842), BMI (Yengo et al; n_GWAS=688,633; n_Lifelines=11,842), diastolic blood pressure (Evangelou et al; n_GWAS=756,595; n_Lifelines=11,832), and T2D (Xue et al; n_cases_GWAS=62,693; n_cases_Lifelines=179). To evaluate our method in more traits, we performed another set of analysis using the summary statistics from the FinnGen data set (max n=342,499) for training, with the 350K unrelated UKB individuals of European ancestry as validation. We selected 5 common diseases in FinnGen that have at least 1,000 cases in the UKB. Additionally, we have analysed the summary statistics from 8 traits in Biobank Japan using the UKB EAS samples as LD reference, and another 8 traits in PAGE using the UKB AFR samples as LD reference. Put all together, we have analysed 25 sets of external summary statistics from traits across a range of categories (Supplementary Tables 5-7). The results of these analyses are shown in the revised Figures 3b and Figure 4c,d. Our results showed that SBayesRC outperformed LDpred2, LDpred-funct and MegaPRS in out-of- sample prediction and outperformed PRS-CSx in cross-ancestry prediction, when external summary statistics were used for training.

In our analysis of FinnGen summary statistics, we used the UKB EUR samples as LD reference because the individual genotype data for the FinnGen population are not publicly available. In this case, we observed a convergence problem in some of the traits analysed, when using our default settings in SBayesRC. Through investigation, we found the problem to be related to the specification of the cut-off value (𝜌) for the variance explained in LD by the selected eigenvalues. The default value of 𝜌 was set to be 0.995, based on the simulation study using the UKB data. However, for some traits in FinnGen, a lower 𝜌 value was required to address the convergence in SBayesRC. The intuitive explanation is that when the GWAS sample is different from the reference sample in LD structure (e.g., FinnGen is an

20

[Figure on PDF page 21](../assets/supp_figs/s004-figure-p0021-000.jpg)

isolated population), the LD matrix computed from the reference requires stronger regularization, which can be achieved by only including principal components with relatively large eigenvalues, since those with small eigenvalues are subject to LD variation. In other words, the 𝜌 value that optimises the prediction performance is data set dependent, particularly contingent on the LD differences between GWAS and reference samples. We have now improved our method to automatically choose the optimal 𝜌 value by performing a pseudo validation based on the summary statistics, following the strategy of Zhang et al (the MegaPRS paper). In brief, we added a tuning step which will partition the observed summary statistics into training and test sets, run multiple short MCMC chains with different 𝜌 values, and then use the one that gives the highest prediction accuracy in the test set for the formal analysis. In contrast to Zhang et al, our approach for partitioning the summary statistics does not require individual genotype data, but only eigenvalues and eigenvectors of the LD matrix, which have already been generated for the low-rank model. Additionally, it is of note that this tuning step is only used to find the optimal 𝜌 value and all the other model parameters remain estimated from the data. The details of this new component of our method are described in the Supplementary Note and the main text at lines 173-176 and 643-649.

6. Have the authors considered using AFR instead of EAS summary statistics (e.g. PAGE) to derive PRS for trans-ancestry prediction in AFR populations?

In the revised manuscript, we have included the analysis of 8 traits from the PAGE data set that were in common with those in the UKB data set of African ancestries. Similar to the analysis for EAS ancestry, we ran SBayesRC using UKB EUR data set only and SBayesRC-multi which combines data from both UKB EUR samples and PAGE samples, and compared to the performance of PRS-CSx. In SBayesRC- multi, we first ran SBayesRC in UKB EUR data set and PAGE data set separately and then used a tuning sample of 500 individuals of AFR ancestry in the UKB to generate African-specific SNP effect estimates. Likewise, we ran PRS-CSx using the same data with only UKB EUR data set for training or with UKB EUR and PAGE AFR data sets analysed jointly for training (with a tuning step). The prediction accuracy was calculated in the hold-out UKB AFR samples independent of the 500 tuning samples. As expected, in both SBayesRC and PRS-CSx, using both EUR and AFR data sets for training was superior to using EUR data set only. However, SBayesRC with annotations using EUR data set only has readily outperformed PRS-CSx with both EUR and AFR data as input, regardless of 1M or 7M SNPs used in SBayesRC (PRS- CSx cannot use 7M SNPs due to computational constraint). When SBayesRC-multi was used, with 7M SNPs, annotations, and AFR data from PAGE, the difference to PRS-CSx increased to 40.9% ( 𝑅SBayesRC 2 −𝑅PRS−CSx 2 𝑅PRS−CSx 2 ) on average across traits, suggesting that information from annotations at dense SNPs

can outweigh that from the summary statistics from the target population. These results are consistent with the observations from the trans-ancestry prediction for EAS (Figure 4c). We have included this new result in the revised Figure 4d,  lines 354-359 in Results and lines 853-880 in Methods of the revised manuscript.

21

[Figure on PDF page 22](../assets/supp_figs/s004-figure-p0022-000.jpg)

Minor:

1. In Figure 1a, why is Anno3 of "causal variant unobserved" different with Anno3 of "causal variant observed"?

We have improved Figure 1a to better convey the idea that when the causal variant is not observed, its effect can be captured through LD by a SNP that has a different annotation from the causal variant.

2. Results from PRS-CSx should be included in Figure 4.

The results from PRS-CSx have already been shown in Figure 4c and 4d (the first column). We have made this clear in the figure legend.

3. SBayesRC uses 5 mixture components. I was wondering whether increasing or decreasing the number of components could affect the performance.

The impact of the number of mixture component on the prediction accuracy has been explored in the SBayesR paper (Lloyd-Jones et al). In the revised manuscript, we run SBayesRC with 4 or 6 mixture components (default is 5) in the simulation, which was based on 5 components, as well as in one quantitative trait (height) and one disease trait (T2D) and found negligible difference to the default setting of 5 components. This result is now shown in Supplementary Figure 13 and in the main text at lines 227- 230.

4. Tuning parameters of LDpred2 and PRS-CSx should be listed in the method section.

We have added these details in the revised manuscript (lines 814-817, 824-827 and 870-875).

5. In Figure 7c, what does the x-axis of "zero effect" mean? Why do some categories have negative values?

Figure 7c shows the deviation of proportion of SNPs in each effect size distribution (from zero, small to very large effect sizes) for a functional category to the overall proportion of genome-wide SNPs across functional categories. We have made this clear in the figure legend (lines 1268-1270)

22

[Figure on PDF page 23](../assets/supp_figs/s004-figure-p0023-000.jpg)

# Decision Letter, first revision:

## 23rd June 2023

Dear Jian,

Your revised Analysis "Leveraging functional genomic annotations and genome coverage to improve polygenic prediction of complex traits within and between ancestries" has been seen by two of the original referees. You will see from their comments below that, while they find the manuscript improved, they have highlighted a few ongoing concerns. We remain interested in the possibility of publishing your study in Nature Genetics, but we would like to consider your response to these concerns in the form of a further revision before we make a final decision on publication.

As before, to guide the scope of the revisions, the editors discuss the referee reports in detail within the team, including with the chief editor, with a view to identifying key priorities that should be addressed in revision, and sometimes overruling referee requests that are deemed beyond the scope of the current study. In this case, we ask that you revise the figures for clarity as requested by Reviewer #1 and extend the benchmarking analyses where feasible as requested by Reviewer #3. We again hope that you will find this prioritized set of referee points to be useful when revising your study. Please do not hesitate to get in touch if you would like to discuss these issues further.

We therefore invite you to revise your manuscript again taking into account all reviewer and editor comments. Please highlight all changes in the manuscript text file. At this stage, we will need you to upload a copy of the manuscript in MS Word .docx or similar editable format.

We are committed to providing a fair and constructive peer-review process. Do not hesitate to contact us if there are specific requests from the reviewers that you believe are technically impossible or unlikely to yield a meaningful outcome.

When revising your manuscript:

*1) Include a “Response to referees” document detailing, point-by-point, how you addressed each referee comment. If no action was taken to address a point, you must provide a compelling argument. This response will be sent back to the referees along with the revised manuscript.

*2) If you have not done so already, please begin to revise your manuscript so that it conforms to our Analysis format instructions, available here.

Refer also to any guidelines provided in this letter.

*3) Include a revised version of any required Reporting Summary: https://www.nature.com/documents/nr-reporting-summary.pdf

It will be available to referees (and, potentially, statisticians) to aid in their evaluation if the manuscript goes back for peer review. A revised checklist is essential for re-review of the paper.

23

[Figure on PDF page 24](../assets/supp_figs/s004-figure-p0024-000.jpg)

Please be aware of our guidelines on digital image standards.

Please use the link below to submit your revised manuscript and related files:

[redacted]

Note: This URL links to your confidential home page and associated information about manuscripts you may have submitted, or that you are reviewing for us. If you wish to forward this email to co- authors, please delete the link to your homepage.

We hope to receive your revised manuscript within 4-8 weeks. If you cannot send it within this time, please let us know.

Please do not hesitate to contact me if you have any questions or would like to discuss these revisions further.

Nature Genetics is committed to improving transparency in authorship. As part of our efforts in this direction, we are now requesting that all authors identified as ‘corresponding author’ on published papers create and link their Open Researcher and Contributor Identifier (ORCID) with their account on the Manuscript Tracking System (MTS), prior to acceptance. ORCID helps the scientific community achieve unambiguous attribution of all scholarly contributions. You can create and link your ORCID from the home page of the MTS by clicking on ‘Modify my Springer Nature account’. For more information please visit please visit www.springernature.com/orcid.

We look forward to seeing the revised manuscript and thank you for the opportunity to review your work.

Sincerely, Kyle

Kyle Vogan, PhD Senior Editor Nature Genetics https://orcid.org/0000-0001-9565-9665

Referee expertise:

Referee #1: Genetics, statistical methods, polygenic prediction Referee #3: Genetics, statistical methods, polygenic prediction

Reviewers' Comments:

Reviewer #1: Remarks to the Author:

24

[Figure on PDF page 25](../assets/supp_figs/s004-figure-p0025-000.jpg)

In this update, the authors have included additional analyses, incorporating MegaPRS and external GWAS for different ancestries such as African (PAGE). This has greatly improved the current paper and has consistently demonstrated the performance gain of SBayesRC. While the content of the current paper has greatly improved, the figure illustrations can be improved. Specifically, I have the following comments:

1. The only question I have, which is more for my own curiosity, with regarding to the performance of SBayesRC is whether the inclusion of “junk” annotations will have a negative impact on SBayesRC? For example, if a random set of annotations were added, will performance of SBayesRC reduce? This is not major, and is really only for my own curiousity.

2. I struggle to find the exact analyses that was done to generate Figure 2. Based on the description in the method section, it was suggested that traits with heritability of 0.1 and 0.5 were both simulated. However, looking at Figure 2a and Figure 2b, it’s likely that only the results from heritability of 0.5 were reported? Would it be possible to highlight that in the legend, or with a horizontal dotted line (with description / legend) to show what’s the “expected” prediction accuracy under the simulation?

3. For Figure 2c, the legend stated that it was the improvement of prediction accuracy using SBayesRC comparing to other methods, but there are boxes with color of SBayesRC. This raises two questions: does the y-axis show the relative difference in prediction accuracy (e.g. R2 from (SBayesRC – R2 from X) / R2 from X, where X are the different methods), or does it show the absolute difference in R2? But for either, it is rather strange that SBayesRC is included in the figure. Or did the authors intend to show the absolute / relative difference between the methods and SBayesR instead? And what does the dotted horizonal line represent?

4. For Figure 2d-f, it is difficult to differentiate the alpha change between the annotation classes, maybe it’s better if a different shade of color is used? e.g. dark red vs pink (or #D81B60 vs #FFC107 for colorblind friendly contrast).

5. Similarly, the color palette for Figure 3 is rather difficult to read. Maybe you can try to use some of the palette provided by ggsci package instead of the ggplot default to make it slightly easier.

Minor comment:

1. Figure 4’s legend, B should be b instead

Reviewer #3: Remarks to the Author:

I thank the authors for addressing the majority of my previous comments. I have also tested SBayesRC myself and found that SBayesRC converges on external summary statistics that SBayesR is unable to. I have two more questions.

My main concern is that the improvement of SBayesRC over MegaPRS is marginal (4.1 %). Perhaps

25

[Figure on PDF page 26](../assets/supp_figs/s004-figure-p0026-000.jpg)

the authors could analyze more traits to more comprehensively demonstrate the improvement of SBayesRC. For example, MegaPRS can be run in the same way as SBayesRC for the comparison of trans-ancestry prediction (Figure 4).

In the simulation setting for comparison of MegaPRS, the effect size \beta_j was simulated from \pi_1 \delta_0 + \pi_2 N(0, \sigma_j^2/100) + \pi_3 N(0, \sigma_j^2/10) + \pi_4 N(0, \sigma_j^2). I think the correct way is to simulate \beta_j from \pi_1 \delta_0 + \pi_2 N(0, s \sigma_j^2/100) + \pi_3 N(0, s \sigma_j^2/10) + \pi_4 N(0, s \sigma_j^2) where s = (\pi_2/100 + \pi_3/10 + \pi_4)^- 1 as the current form does not guarantee the heritability of SNP j is \sigma_j^2.

# Additional Review Material, First Revision

Dear Jian,

We just received an additional review from Reviewer #2 (copied below). When preparing your revision, we ask that you address these comments and include this third review in your point-by- point response. Thanks in advance!

Best, Kyle

Reviewer #2 (Remarks to the Author):

First of all, I apologise to the authors for this late review - I somehow did not receive reminders and this review was lost in my inbox for some time.

Now about the revised paper, I appreciated the efforts put to address the comments from all the reviewers. I read with interest the section on the low rank model and its impact on annotation effects. While quite technical, I did learn something useful.

I do think this paper is ready for publication. A last question I have relates to the availability of the optimised PGS, typically in the PGS catalog. It would be helpful to do so for the traits presented in Figure 3 but the data availability section makes no mention of this. Do the authors plan to change this?

# Author Rebuttal, first revision:

We thank the reviewers for their positive remarks and additional constructive suggestions. We have improved the clarity of figures, made our PGS predictors publicly available, and extended the benchmarking analysis accordingly.  Please find our point-to-point response to the reviewer’s comments in blue.

Reviewers' Comments:

26

[Figure on PDF page 27](../assets/supp_figs/s004-figure-p0027-000.jpg)

# Reviewer #1:

Remarks to the Author:

In this update, the authors have included additional analyses, incorporating MegaPRS and external GWAS for different ancestries such as African (PAGE). This has greatly improved the current paper and has consistently demonstrated the performance gain of SBayesRC. While the content of the current paper has greatly improved, the figure illustrations can be improved. Specifically, I have the following comments:

1. The only question I have, which is more for my own curiosity, with regarding to the performance of SBayesRC is whether the inclusion of “junk” annotations will have a negative impact on SBayesRC? For example, if a random set of annotations were added, will performance of SBayesRC reduce? This is not major, and is really only for my own curiousity.

We shared the same curiosity with the reviewer and have investigated the performance of SBayesRC by simulating random numbers (random samples from a uniform distribution between zero and one) for each of the annotations used in the simulation. The prediction accuracy using random annotations has been shown in the Supplementary Figure 11 in the previous version. The result showed that the inclusion of random annotations in SBayesRC did not adversely affect prediction when the trait heritability was 0.5 but slightly decreased the prediction accuracy (by 2%) when the trait heritability was 0.1. Our further investigation revealed that the slight decrease in prediction accuracy in the case of low heritability is likely due to the increased dispersion of annotation effect estimates around zero when the power of estimation is relatively low (shown in the new panel b of the Supplementary Figure 12 in the revised manuscript). Therefore, we recommend use informative annotations especially for traits with limited GWAS power (e.g., low SNP-based heritability or limited GWAS sample size). We have included the new result (Supplementary Figure 12b) and discussed in lines 594-597.

2. I struggle to find the exact analyses that was done to generate Figure 2. Based on the description in the method section, it was suggested that traits with heritability of 0.1 and 0.5 were both simulated. However, looking at Figure 2a and Figure 2b, it’s likely that only the results from heritability of 0.5 were reported? Would it be possible to highlight that in the legend, or with a horizontal dotted line (with description / legend) to show what’s the “expected” prediction accuracy under the simulation?

We have improved the figure legend as following. “Results were from simulations with trait heritability h2=0.5 (the upper bound of the prediction accuracy). See Supplementary Fig. 4-8 for results from the simulation with h2=0.1.”

27

[Figure on PDF page 28](../assets/supp_figs/s004-figure-p0028-000.jpg)

3. For Figure 2c, the legend stated that it was the improvement of prediction accuracy using SBayesRC comparing to other methods, but there are boxes with color of SBayesRC. This raises two questions: does the y-axis show the relative difference in prediction accuracy (e.g. R2 from (SBayesRC – R2 from X) / R2 from X, where X are the different methods), or does it show the absolute difference in R2? But for either, it is rather strange that SBayesRC is included in the figure. Or did the authors intend to show the absolute / relative difference between the methods and SBayesR instead? And what does the dotted horizonal line represent?

We apologise for the confusion caused by the misleading figure legend. We have revised the figure legend as below. c) The prediction R-squared from SBayesRC, LDpred-funct, and MegaPRS with different SNP densities and with or without annotations. The dashed line shows the prediction R-squared from the benchmarking method SBayesR using HapMap3 SNPs without annotations. Results were from simulations with trait heritability h2=0.5 (the upper bound of the prediction accuracy). See Supplementary Fig. 4-8 for results from the simulation with h2=0.1.

4. For Figure 2d-f, it is difficult to differentiate the alpha change between the annotation classes, maybe it’s better if a different shade of color is used? e.g. dark red vs pink (or #D81B60 vs #FFC107 for colorblind friendly contrast).

We have updated Figure 2d-f accordingly.

5. Similarly, the color palette for Figure 3 is rather difficult to read. Maybe you can try to use some of the palette provided by ggsci package instead of the ggplot default to make it slightly easier.

We have tried other packages but didn’t find a palette that has a significantly better colour contrast. To be consistent across figures, we therefore prefer to keep the current palette in the final version.

Minor comment:

1. Figure 4’s legend, B should be b instead

We have fixed this typo.

Reviewer #2 (Remarks to the Author):

28

[Figure on PDF page 29](../assets/supp_figs/s004-figure-p0029-000.jpg)

First of all, I apologise to the authors for this late review - I somehow did not receive reminders and this review was lost in my inbox for some time.

Now about the revised paper, I appreciated the efforts put to address the comments from all the reviewers. I read with interest the section on the low rank model and its impact on annotation effects. While quite technical, I did learn something useful.

I do think this paper is ready for publication. A last question I have relates to the availability of the optimised PGS, typically in the PGS catalog. It would be helpful to do so for the traits presented in Figure 3 but the data availability section makes no mention of this. Do the authors plan to change this?

We thank the referee for the positive comments. The summary data from GWAS and SNP weights from SBayesRC for constructing the PGS in Fig. 3 can now be found on the GCTB website. We have reservations about directly depositing the SNP weights from SBayesRC to the PGS catalog as the PGS catalog is limited to the additional information that can be provided to the users. Compared to most repositories in the PGS catalog that consist of only a subset of SNPs with significant marginal effects, our SNP weights are joint effects derived from genome-wide SNPs. In this case, it’s important to have matched SNP set between training and validation datasets. This is because if some important SNPs present in the training are missing in the validation, the genetic effects captured by these SNPs will be lost. To maximise the utility of the joint SNP weights, we have included a text on our website for cautions and recommendations of use, as well as the GWAS summary data used in this study for these traits, considering that the users may need to rerun SBayesRC with matched SNPs if significant proportions of SNPs were missing from their target population of prediction. We have included in the data availability lines 921-924.

# Reviewer #3:

Remarks to the Author:

I thank the authors for addressing the majority of my previous comments. I have also tested SBayesRC myself and found that SBayesRC converges on external summary statistics that SBayesR is unable to. I have two more questions.

My main concern is that the improvement of SBayesRC over MegaPRS is marginal (4.1 %). Perhaps the authors could analyze more traits to more comprehensively demonstrate the improvement of SBayesRC. For example, MegaPRS can be run in the same way as SBayesRC for the comparison of trans-ancestry prediction (Figure 4).

We thank the referee for the positive comments and the suggestions. Indeed, SBayesRC has only a small improvement compared to MegaPRS when the LD reference is the same as or closely related to the

29

[Figure on PDF page 30](../assets/supp_figs/s004-figure-p0030-000.jpg)

GWAS sample. However, as shown in Figure 3b of the previous manuscript, SBayesRC gave significantly higher prediction accuracy than MegaPRS across different traits and diseases when using an external LD reference that was independent of the GWAS sample. In the revised manuscript, we have further included the results of analyses within populations of non-European ancestries using external LD reference (specifically, analysis of BBJ data using UKB EAS as LD reference, and analysis of PAGE data using UKB AFR as LD reference) and run MegaPRS in the same way as SBayesRC for trans-ancestry prediction. We found that the benefit of SBayesRC over MegaPRS in this case held in different ancestries as well as in trans-ancestry prediction when EUR and target ancestry data sets were combined to improve prediction. The results are as described in detail below.

1) For within-ancestry prediction, SBayesRC had a significant advantage over MegaPRS when using an external LD reference independent of the GWAS sample. We have previously shown that SBayesRC led to 29.2% higher prediction accuracy than MegaPRS, on average across 5 common diseases, when GWAS summary data from FinnGen was used for training, a random sample of UKB EUR as LD reference, and the full UKB EUR as validation. The significant improvement is likely because through the low-rank approximation SBayesRC better accounted for the sampling variation in LD between the reference and GWAS samples, as a substantial sampling variation is likely to exist between FinnGen and UKB populations, considering Finnish to be an isolated EUR population according to the demographic history. We further evaluated the performance of SBayesRC and MegaPRS in the case of LD sampling variation in EAS and AFR ancestries. For EAS ancestry, we used GWAS summary data from BBJ as training, UKB EAS as LD reference, and UKB EAS as validation. Similarly, for AFR ancestry, we used GWAS summary data from PAGE as training, UKB AFR as LD reference, and UKB AFR as validation. Compared to MegaPRS, SBayesRC led to an improvement of 4.0% and 39.0% prediction accuracy, across 8 traits in EAS and AFR ancestries respectively (Supplementary Fig. 19). The improvement in AFR ancestry was the largest, because there are larger LD differences between UKB AFR and PAGE which has a mixed African ancestry.

2) For trans-ancestry prediction, SBayesRC-multi that combines UKB EUR data set with PAGE data set gave significantly better prediction accuracy than MegaPRS-multi, on average across traits (mean relative prediction accuracy of 38.7% from SBayesRC-multi vs. that of 26.6% from MegaPRS-multi). In addition, the variation in prediction accuracy across traits was smaller in SBayesRC-multi compared to MegaPRS- multi. The benefit of SBayesRC-multi is mainly because the PAGE data was better used in SBayesRC than in MegaPRS, as described above.

Lastly, as per the reviewer’s suggestion, we also ran trans-ancestry prediction in UKB using EUR as training and other ancestries as validation. The results are in general consistent with the within ancestry prediction that SBayesRC has a slightly higher mean prediction accuracy and smaller variance than MegaPRS. In these cases, LD reference was from the same population as the GWAS samples. As described above, the benefit of SBayesRC mainly lies at the circumstances where only an external LD reference is available for the analysis.

30

[Figure on PDF page 31](../assets/supp_figs/s004-figure-p0031-000.jpg)

We have included the new results in Fig. 4, Supplementary Fig. 19, results at lines 275-281, 338-353, and discussed at lines 542-547 in the revised manuscript.

In the simulation setting for comparison of MegaPRS, the effect size \beta_j was simulated from \pi_1 \delta_0 + \pi_2 N(0, \sigma_j^2/100) + \pi_3 N(0, \sigma_j^2/10) + \pi_4 N(0, \sigma_j^2). I think the correct way is to simulate \beta_j from \pi_1 \delta_0 + \pi_2 N(0, s \sigma_j^2/100) + \pi_3 N(0, s \sigma_j^2/10) + \pi_4 N(0, s \sigma_j^2) where s = (\pi_2/100 + \pi_3/10 + \pi_4)^-1 as the current form does not guarantee the heritability of SNP j is \sigma_j^2.

We thank the referee for capturing this. We have simulated using the exactly the same model as described above and rerun the analysis. As shown in the new Supplementary Fig. 15, the results did not change much and the conclusion remains the same. We have revised the text of the Supplementary Note in page 17 accordingly.

# Decision Letter, second revision:

30th October 2023

Dear Jian,

Thank you for submitting your revised manuscript "Leveraging functional genomic annotations and genome coverage to improve polygenic prediction of complex traits within and between ancestries" (NG-AN61070R1). In light of the changes made in response to the referees' comments, we will be happy in principle to publish your study in Nature Genetics as an Analysis pending final revisions to comply with our editorial and formatting guidelines.

We are now performing detailed checks on your paper, and we will send you a checklist detailing our editorial and formatting requirements soon. Please do not upload the final materials or make any revisions until you receive this additional information from us.

Thank you again for your interest in Nature Genetics. Please do not hesitate to contact me if you have any questions.

Sincerely, Kyle

Kyle Vogan, PhD Senior Editor Nature Genetics https://orcid.org/0000-0001-9565-9665

31

[Figure on PDF page 32](../assets/supp_figs/s004-figure-p0032-000.jpg)

# Final Decision Letter:

In reply please quote: NG-A61070R2 Zeng

5th March 2024

Dear Jian,

I am delighted to say that your manuscript "Leveraging functional genomic annotations and genome coverage to improve polygenic prediction of complex traits within and between ancestries" has been accepted for publication in an upcoming issue of Nature Genetics.

Over the next few weeks, your paper will be copyedited to ensure that it conforms to Nature Genetics style. Once your paper is typeset, you will receive an email with a link to choose the appropriate publishing options for your paper and our Author Services team will be in touch regarding any additional information that may be required.

After the grant of rights is completed, you will receive a link to your electronic proof via email with a request to make any corrections within 48 hours. If, when you receive your proof, you cannot meet this deadline, please inform us at rjsproduction@springernature.com immediately.

You will not receive your proofs until the publishing agreement has been received through our system.

Due to the importance of these deadlines, we ask that you please let us know now whether you will be difficult to contact over the next month. If this is the case, we ask you provide us with the contact information (email, phone and fax) of someone who will be able to check the proofs on your behalf, and who will be available to address any last-minute problems.

Your paper will be published online after we receive your corrections and will appear in print in the next available issue. You can find out your date of online publication by contacting the Nature Press Office (press@nature.com) after sending your e-proof corrections.

You may wish to make your media relations office aware of your accepted publication, in case they consider it appropriate to organize some internal or external publicity. Once your paper has been scheduled you will receive an email confirming the publication details. This is normally 3-4 working days in advance of publication. If you need additional notice of the date and time of publication, please let the production team know when you receive the proof of your article to ensure there is sufficient time to coordinate. Further information on our embargo policies can be found here: https://www.nature.com/authors/policies/embargo.html

Before your paper is published online, we will be distributing a press release to news organizations worldwide, which may very well include details of your work. We are happy for your institution or funding agency to prepare its own press release, but it must mention the embargo date and Nature Genetics. Our Press Office may contact you closer to the time of publication, but if you or your Press Office have any enquiries in the meantime, please contact press@nature.com.

32

[Figure on PDF page 33](../assets/supp_figs/s004-figure-p0033-000.jpg)

Acceptance is conditional on the data in the manuscript not being published elsewhere, or announced in the print or electronic media, until the embargo/publication date. These restrictions are not intended to deter you from presenting your data at academic meetings and conferences, but any enquiries from the media about papers not yet scheduled for publication should be referred to us.

Please note that Nature Genetics is a Transformative Journal (TJ). Authors may publish their research with us through the traditional subscription access route or make their paper immediately open access through payment of an article-processing charge (APC). Authors will not be required to make a final decision about access to their article until it has been accepted. Find out more about Transformative Journals

Authors may need to take specific actions to achieve compliance with funder and institutional open access mandates. If your research is supported by a funder that requires immediate open access (e.g. according to Plan S principles), then you should select the gold OA route, and we will direct you to the compliant route where possible. For authors selecting the subscription publication route, the journal’s standard licensing terms will need to be accepted, including <a href="https://www.nature.com/nature-portfolio/editorial-policies/self-archiving-and-license-to- publish. Those licensing terms will supersede any other terms that the author or any third party may assert apply to any version of the manuscript.

If you have any questions about our publishing options, costs, Open Access requirements, or our legal forms, please contact ASJournals@springernature.com

If you have posted a preprint on any preprint server, please ensure that the preprint details are updated with a publication reference, including the DOI and a URL to the published version of the article on the journal website.

To assist our authors in disseminating their research to the broader community, our SharedIt initiative provides you with a unique shareable link that will allow anyone (with or without a subscription) to read the published article. Recipients of the link with a subscription will also be able to download and print the PDF.

As soon as your article is published, you will receive an automated email with your shareable link.

You can now use a single sign-on for all your accounts, view the status of all your manuscript submissions and reviews, access usage statistics for your published articles and download a record of your refereeing activity for the Nature journals.

An online order form for reprints of your paper is available at https://www.nature.com/reprints/author-reprints.html. Please let your coauthors and your institutions' public affairs office know that they are also welcome to order reprints by this method.

If you have not already done so, we invite you to upload the step-by-step protocols used in this manuscript to the Protocols Exchange, part of our on-line web resource, natureprotocols.com. If you complete the upload by the time you receive your manuscript proofs, we can insert links in your article that lead directly to the protocol details. Your protocol will be made freely available upon publication of your paper. By participating in natureprotocols.com, you are enabling researchers to more readily reproduce or adapt the methodology you use. Natureprotocols.com is fully searchable, providing your

33

[Figure on PDF page 34](../assets/supp_figs/s004-figure-p0034-000.jpg)

protocols and paper with increased utility and visibility. Please submit your protocol to https://protocolexchange.researchsquare.com/. After entering your nature.com username and password you will need to enter your manuscript number (NG-A61070R2). Further information can be found at https://www.nature.com/nature-portfolio/editorial-policies/reporting-standards#protocols

Sincerely, Kyle

Kyle Vogan, PhD Senior Editor Nature Genetics https://orcid.org/0000-0001-9565-9665

34

### Contents: List of Supplementary Tables

List of Supplemenary Tables:

[Contents: List of Supplementary Tables](../assets/supp_table/supplementary-table-contents.csv)

Source: 41588_2024_1704_MOESM4_ESM.xlsx; worksheet: Contents.
Ordinal 1 (sheet 'Contents'), 11 rows x 1 column (10 non-empty cells; A2 blank). Enumerates Supplementary Tables 1-9 with their titles. General format.

| List of Supplemenary Tables: |
| --- |
|  |
| Supplementary Table 1. Description of 50 UKB complex traits analysed in this study  |
| Supplementary Table 2. Estimation of SNP-based heritability for 28 independent UKB traits |
| Supplementary Table 3. Mean prediction accuracy, regression slope and AUC in the UKB cross-validation for 28 independent traits |
| Supplementary Table 4. Cross-ancestry prediction accuracy in 18 well-powered independent UKB traits |
| Supplementary Table 5. Cross-ancestry prediction accuracy in UKB East Asian population using training data from UKB-EUR and BBJ (Biobank Japan) for 8 traits |
| Supplementary Table 6. Cross-ancestry prediction accuracy in UKB African population using training data from UKB-EUR and PAGE (mixed African ancestry) for 8 traits |
| Supplementary Table 7. Out-of-sample prediction accuracy in European ancestry using external summary statistics |
| Supplementary Table 8. Mean prediction accuracy, regression slope and AUC in the UKB cross-validation for the remaining 22 non-independent traits |
| Supplementary Table 9. Contribution of selected functional categories to prediction accuracy and estimation of functional genetic architecture in 28 complex traits |

### Supplementary Table 1: Description of 50 UKB complex traits analysed in this study



[Supplementary Table 1: Description of 50 UKB complex traits analysed in this study](../assets/supp_table/supplementary-table-1.csv)

Source: 41588_2024_1704_MOESM4_ESM.xlsx; worksheet: ST1.
Sheet 'ST1', 53 rows x 11 columns (562 non-empty cells). Header row 3: Trait Acronym, Trait Description, UKB ID, N.EUR, N.CVmean, N.SAS, N.EAS, N.AFR, N.total, Category, Independent. 50 trait rows (rows 4-53). All General format; counts are held as strings.



### Supplementary Table 2: Estimation of SNP-based heritability for 28 independent UKB traits

For binary traits, the estimate is mapped to the liability scale, assuming the population prevalence is the same as the sample prevalence in the UK Biobank.

[Supplementary Table 2: Estimation of SNP-based heritability for 28 independent UKB traits](../assets/supp_table/supplementary-table-2.csv)

Source: 41588_2024_1704_MOESM4_ESM.xlsx; worksheet: ST2.
CSV retains raw numeric values, not Excel display formatting (including percentages, dates and zero-padding); inspect source formats when interpreting units.
Sheet 'ST2', 199 rows x 5 columns (707 non-empty cells). Header row 3: Trait, Method, hsq estimation, Prevalence, hsq in liability scale. 196 data rows (196 = 28 traits x 7 methods). hsq/Prevalence columns carry number_format 0.000 (3 decimals); CSV holds raw doubles.



### Supplementary Table 3: Mean prediction accuracy, regression slope and AUC in the UKB cross-validation for 28 independent traits



[Supplementary Table 3: Mean prediction accuracy, regression slope and AUC in the UKB cross-validation for 28 independent traits](../assets/supp_table/supplementary-table-3.csv)

Source: 41588_2024_1704_MOESM4_ESM.xlsx; worksheet: ST3.
CSV retains raw numeric values, not Excel display formatting (including percentages, dates and zero-padding); inspect source formats when interpreting units.
Sheet 'ST3', 451 rows x 8 columns (2633 non-empty cells). Header row 3: Trait, SNPset, Method, Prediction accuracy (r2), Slope, AUC, Effect/SD_PRS, OR/SD_PRS. Numeric columns D,E,F,G number_format 0.000 (3 decimals); CSV holds raw doubles.



### Supplementary Table 4: Cross-ancestry prediction accuracy in 18 well-powered independent UKB traits



[Supplementary Table 4: Cross-ancestry prediction accuracy in 18 well-powered independent UKB traits](../assets/supp_table/supplementary-table-4.csv)

Source: 41588_2024_1704_MOESM4_ESM.xlsx; worksheet: ST4.
CSV retains raw numeric values, not Excel display formatting (including percentages, dates and zero-padding); inspect source formats when interpreting units.
Sheet 'ST4', 435 rows x 5 columns (2166 non-empty cells). Header row 3: Trait, Method, Population, SNPset, Prediction accuracy (r2). Column E number_format 0.000 (3 decimals); CSV holds raw doubles.



### Supplementary Table 5: Cross-ancestry prediction accuracy in UKB East Asian population using training data from UKB-EUR and BBJ (Biobank Japan) for 8 traits



[Supplementary Table 5: Cross-ancestry prediction accuracy in UKB East Asian population using training data from UKB-EUR and BBJ (Biobank Japan) for 8 traits](../assets/supp_table/supplementary-table-5.csv)

Source: 41588_2024_1704_MOESM4_ESM.xlsx; worksheet: ST5.
CSV retains raw numeric values, not Excel display formatting (including percentages, dates and zero-padding); inspect source formats when interpreting units.
Sheet 'ST5', 155 rows x 5 columns (766 non-empty cells). Header row 3: Trait, Training Data, Method, SNPset, Prediction accuracy (r2). Column E number_format 0.0000 (4 decimals); CSV holds raw doubles.



### Supplementary Table 6: Cross-ancestry prediction accuracy in UKB African population using training data from UKB-EUR and PAGE (mixed African ancestry) for 8 traits



[Supplementary Table 6: Cross-ancestry prediction accuracy in UKB African population using training data from UKB-EUR and PAGE (mixed African ancestry) for 8 traits](../assets/supp_table/supplementary-table-6.csv)

Source: 41588_2024_1704_MOESM4_ESM.xlsx; worksheet: ST6.
CSV retains raw numeric values, not Excel display formatting (including percentages, dates and zero-padding); inspect source formats when interpreting units.
Sheet 'ST6', 154 rows x 5 columns (761 non-empty cells). Header row 3: Trait, Training Data, Method, SNPset, Prediction accuracy (r2). Column E number_format 0.0000 (4 decimals); CSV holds raw doubles.



### Supplementary Table 7: Out-of-sample prediction accuracy in European ancestry using external summary statistics

We used data from FinnGen for training and UKB for validation or data from published meta-GWAS for training and Lifelines for validation.

[Supplementary Table 7: Out-of-sample prediction accuracy in European ancestry using external summary statistics](../assets/supp_table/supplementary-table-7.csv)

Source: 41588_2024_1704_MOESM4_ESM.xlsx; worksheet: ST7.
CSV retains raw numeric values, not Excel display formatting (including percentages, dates and zero-padding); inspect source formats when interpreting units.
Sheet 'ST7', 40 rows x 4 columns (150 non-empty cells; the sheet declares 5 columns but column B is empty/unused in the header). Header row 4 (row 3 blank): Trait, Method, Prediction accuracy(r2), Category. Column C number_format 0.0000 (4 decimals); CSV holds raw doubles.

| Supplementary Table 7. Out-of-sample prediction accuracy in European ancestry using external summary statistics |  |  |  |
| --- | --- | --- | --- |
| We used data from FinnGen for training and UKB for validation or data from published meta-GWAS for training and Lifelines for validation. |  |  |  |
|  |  |  |  |
| Trait | Method | Prediction accuracy(r2) | Category |
| Asthma | LDpred2 | 8.6554009824856299E-3 | FinnGen -> UKB |
| Asthma | LDpred-funct | 5.7445115351363301E-3 | FinnGen -> UKB |
| Asthma | MegaPRS | 7.9389475798680199E-3 | FinnGen -> UKB |
| Asthma | SBayesRC | 1.0869763094286399E-2 | FinnGen -> UKB |
| BC | LDpred2 | 2.1977178999442001E-2 | FinnGen -> UKB |
| BC | LDpred-funct | 7.9602111626680995E-3 | FinnGen -> UKB |
| BC | MegaPRS | 1.6812615769146801E-2 | FinnGen -> UKB |
| BC | SBayesRC | 2.33307045392399E-2 | FinnGen -> UKB |
| HBP | LDpred2 | 3.6770491765593799E-2 | FinnGen -> UKB |
| HBP | LDpred-funct | 3.3872829614308202E-2 | FinnGen -> UKB |
| HBP | MegaPRS | 3.4298444211490198E-2 | FinnGen -> UKB |
| HBP | SBayesRC | 4.0361725977480903E-2 | FinnGen -> UKB |
| T2D | LDpred2 | 4.04208014138175E-2 | FinnGen -> UKB |
| T2D | LDpred-funct | 3.4744989993348699E-2 | FinnGen -> UKB |
| T2D | MegaPRS | 3.5790106349433699E-2 | FinnGen -> UKB |
| T2D | SBayesRC | 4.5958211699648199E-2 | FinnGen -> UKB |
| GLAUC | LDpred2 | 2.02960239446319E-2 | FinnGen -> UKB |
| GLAUC | LDpred-funct | 9.6906128355571698E-3 | FinnGen -> UKB |
| GLAUC | MegaPRS | 1.9042772068056501E-2 | FinnGen -> UKB |
| GLAUC | SBayesRC | 2.3655125817214101E-2 | FinnGen -> UKB |
| T2D | LDpred2 | 2.9325161667107899E-2 | Meta -> LifeLines |
| T2D | LDpred-funct | 3.1596080189325498E-2 | Meta -> LifeLines |
| T2D | MegaPRS | 3.4946939782624399E-2 | Meta -> LifeLines |
| T2D | SBayesRC | 4.0617071444546703E-2 | Meta -> LifeLines |
| DBP | LDpred2 | 9.1724637362401204E-2 | Meta -> LifeLines |
| DBP | LDpred-funct | 9.3823849855162303E-2 | Meta -> LifeLines |
| DBP | MegaPRS | 0.106522501044096 | Meta -> LifeLines |
| DBP | SBayesRC | 0.111594122719554 | Meta -> LifeLines |
| BMI | LDpred2 | 0.15149667860319899 | Meta -> LifeLines |
| BMI | LDpred-funct | 0.15128927646881801 | Meta -> LifeLines |
| BMI | MegaPRS | 0.15964472008395 | Meta -> LifeLines |
| BMI | SBayesRC | 0.16201332478796501 | Meta -> LifeLines |
| HT | LDpred2 | 0.381953112187363 | Meta -> LifeLines |
| HT | LDpred-funct | 0.36309628059732302 | Meta -> LifeLines |
| HT | MegaPRS | 0.39608150764551697 | Meta -> LifeLines |
| HT | SBayesRC | 0.39728918785943601 | Meta -> LifeLines |

### Supplementary Table 8: Mean prediction accuracy, regression slope and AUC in the UKB cross-validation for the remaining 22 non-independent traits



[Supplementary Table 8: Mean prediction accuracy, regression slope and AUC in the UKB cross-validation for the remaining 22 non-independent traits](../assets/supp_table/supplementary-table-8.csv)

Source: 41588_2024_1704_MOESM4_ESM.xlsx; worksheet: ST8.
CSV retains raw numeric values, not Excel display formatting (including percentages, dates and zero-padding); inspect source formats when interpreting units.
Sheet 'ST8', 113 rows x 8 columns (589 non-empty cells). Header row 3: Trait, Method, SNP_Annot, Prediction accuracy (r2), Slope, AUC, Effect/SD_PRS, OR/SD_PRS. Numeric columns D,E,F,G number_format 0.000 (3 decimals); CSV holds raw doubles.



### Supplementary Table 9: Contribution of selected functional categories to prediction accuracy and estimation of functional genetic architecture in 28 complex traits



[Supplementary Table 9: Contribution of selected functional categories to prediction accuracy and estimation of functional genetic architecture in 28 complex traits](../assets/supp_table/supplementary-table-9.csv)

Source: 41588_2024_1704_MOESM4_ESM.xlsx; worksheet: ST9.
Sheet 'ST9', 28 rows x 11 columns (287 non-empty cells). Header row 3: Annotation, Annotation_BaselineLD 2.2, perSNP_hsq_enrich, Dist_zero_effect, Dist_small_effect, Dist_medium_effect, Dist_large_effect, Dist_veryLarge_effect, Proportion_SNPs, Proportion_Prediction_Accuracy, perSNP_Predictability_enrich. Values are 'mean +/- sd' text strings (General format); 25 numeric + 262 string cells.

| Supplementary Table 9. Contribution of selected functional categories to prediction accuracy and estimation of functional genetic architecture in 28 complex traits |  |  |  |  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |  |  |  |  |
| Annotation | Annotation_BaselineLD 2.2 | perSNP_hsq_enrich | Dist_zero_effect | Dist_small_effect | Dist_medium_effect | Dist_large_effect | Dist_veryLarge_effect | Proportion_SNPs | Proportion_Prediction_Accuracy | perSNP_Predictability_enrich |
| Non_synonymous | non_synonymous | 18.75 ± 2.54 | -3.64e-03 ± 4.15e-04 | 3.58e-03 ± 4.12e-04 | 4.83e-05 ± 6.32e-06 | 6.74e-06 ± 2.09e-06 | 1.01e-06 ± 4.96e-07 | 0.31 | 12.92 ± 1.16 | 41.41 ± 3.72 |
| Promoter_Ancient | Ancient_Sequence_Age_Human_Promoter | 11.04 ± 0.97 | -4.00e-03 ± 5.12e-04 | 3.97e-03 ± 5.10e-04 | 2.85e-05 ± 6.26e-06 | 1.27e-06 ± 5.10e-07 | 5.85e-08 ± 4.40e-08 | 0.46 | 12.67 ± 0.71 | 27.74 ± 1.56 |
| Promoter_ExAC | Human_Promoter_Villar_ExAC | 9.63 ± 0.75 | -5.15e-03 ± 6.49e-04 | 5.12e-03 ± 6.47e-04 | 3.32e-05 ± 6.86e-06 | 9.81e-07 ± 2.68e-07 | 8.97e-08 ± 3.58e-08 | 0.27 | 6.89 ± 0.38 | 25.09 ± 1.39 |
| GERP | GERP.RSsup4 | 9.34 ± 0.59 | -4.13e-03 ± 5.23e-04 | 4.09e-03 ± 5.20e-04 | 3.00e-05 ± 6.28e-06 | 1.53e-06 ± 7.96e-07 | 3.93e-07 ± 2.37e-07 | 0.98 | 21.54 ± 1.37 | 22.03 ± 1.4 |
| Intron.flank | Intron_UCSC.flanking.500 | 8.82 ± 0.93 | 2.36e-04 ± 2.06e-04 | -2.46e-04 ± 2.04e-04 | 8.95e-06 ± 3.11e-06 | 1.01e-06 ± 5.05e-07 | 2.33e-07 ± 1.22e-07 | 1 | 19.69 ± 1.3 | 19.7 ± 1.3 |
| Coding | Coding_UCSC | 7.58 ± 0.63 | -3.96e-03 ± 4.08e-04 | 3.94e-03 ± 4.07e-04 | 2.15e-05 ± 5.18e-06 | 1.29e-06 ± 5.62e-07 | 4.00e-07 ± 2.43e-07 | 1.56 | 25.86 ± 1.32 | 16.55 ± 0.85 |
| Conserved_Mammal46 | Conserved_Mammal_phastCons46way | 6.95 ± 0.35 | -8.58e-04 ± 2.11e-04 | 8.27e-04 ± 2.10e-04 | 3.02e-05 ± 5.46e-06 | 1.13e-06 ± 3.94e-07 | 1.43e-07 ± 7.30e-08 | 2.48 | 37.4 ± 1.99 | 15.06 ± 0.8 |
| Conserved_Primate | Conserved_Primate_phastCons46way | 6.78 ± 0.41 | -4.06e-03 ± 9.35e-04 | 3.96e-03 ± 9.28e-04 | 1.02e-04 ± 2.78e-05 | 2.11e-06 ± 9.50e-07 | 7.21e-08 ± 4.00e-08 | 2.29 | 34.62 ± 2.35 | 15.09 ± 1.02 |
| Conserved_Mammal29 | Conserved_LindbladToh | 6.71 ± 0.28 | -5.42e-03 ± 6.43e-04 | 5.40e-03 ± 6.45e-04 | 2.76e-05 ± 7.16e-06 | 5.37e-07 ± 1.74e-07 | 6.58e-08 ± 3.30e-08 | 2.86 | 40.53 ± 1.85 | 14.15 ± 0.64 |
| Promoter_Ancient.flank | Ancient_Sequence_Age_Human_Promoter.flanking.500 | 6.1 ± 1.02 | -1.48e-03 ± 3.05e-04 | 1.47e-03 ± 3.04e-04 | 1.55e-05 ± 3.24e-06 | 6.17e-07 ± 2.30e-07 | 1.61e-07 ± 1.04e-07 | 0.55000000000000004 | 10.39 ± 0.76 | 18.91 ± 1.39 |
| Enhancer_Ancient | Ancient_Sequence_Age_Human_Enhancer | 6.04 ± 0.58 | -1.83e-03 ± 3.07e-04 | 1.81e-03 ± 3.05e-04 | 1.61e-05 ± 4.35e-06 | 3.53e-07 ± 2.62e-07 | 8.11e-08 ± 5.32e-08 | 0.56999999999999995 | 9.19 ± 0.54 | 16.01 ± 0.93 |
| TSS | TSS_Hoffman | 5.97 ± 0.45 | -1.07e-03 ± 2.18e-04 | 1.06e-03 ± 2.17e-04 | 9.34e-06 ± 2.43e-06 | 5.26e-07 ± 2.41e-07 | 1.66e-07 ± 1.13e-07 | 1.83 | 24.35 ± 1.07 | 13.3 ± 0.59 |
| Promoter_Human | Human_Promoter_Villar | 5.95 ± 0.49 | -5.79e-04 ± 3.26e-04 | 5.66e-04 ± 3.23e-04 | 9.41e-06 ± 4.54e-06 | 2.89e-06 ± 1.87e-06 | 8.93e-07 ± 6.32e-07 | 1.59 | 20.27 ± 0.92 | 12.79 ± 0.58 |
| UTR5 | UTR_5_UCSC | 5.89 ± 0.55 | -1.30e-04 ± 2.21e-04 | 1.24e-04 ± 2.19e-04 | 5.80e-06 ± 1.96e-06 | 2.85e-07 ± 2.76e-07 | 5.50e-08 ± 4.87e-08 | 0.56000000000000005 | 9.15 ± 0.52 | 16.21 ± 0.92 |
| Conserved_Vertebrate | Conserved_Vertebrate_phastCons46way | 5.58 ± 0.27 | -7.27e-04 ± 2.02e-04 | 7.05e-04 ± 2.02e-04 | 2.13e-05 ± 4.38e-06 | 6.39e-07 ± 3.08e-07 | 9.31e-08 ± 4.85e-08 | 3.17 | 38.23 ± 2.03 | 12.08 ± 0.64 |
| BivFlnk | BivFlnk | 5.24 ± 0.23 | -2.15e-03 ± 6.11e-04 | 2.12e-03 ± 6.06e-04 | 3.10e-05 ± 8.16e-06 | 8.25e-07 ± 4.81e-07 | 5.14e-08 ± 2.74e-08 | 1.38 | 16.19 ± 0.69 | 11.7 ± 0.5 |
| Enhancer_Human | Enhancer_Andersson | 5.01 ± 0.98 | -2.31e-03 ± 9.82e-04 | 2.30e-03 ± 9.79e-04 | 1.58e-05 ± 3.92e-06 | 5.03e-07 ± 2.31e-07 | 7.62e-08 ± 4.93e-08 | 0.45 | 6.75 ± 0.91 | 15.08 ± 2.03 |
| Synonymous | synonymous | 4.04 ± 0.33 | 2.66e-03 ± 2.50e-04 | -2.65e-03 ± 2.50e-04 | -4.13e-06 ± 9.18e-07 | -2.77e-07 ± 1.33e-07 | 1.21e-08 ± 2.04e-08 | 0.34 | 5.71 ± 0.37 | 16.7 ± 1.1 |
| UTR3 | UTR_3_UCSC | 3.91 ± 0.25 | -4.20e-04 ± 2.53e-04 | 4.08e-04 ± 2.51e-04 | 1.19e-05 ± 3.04e-06 | 3.21e-07 ± 1.78e-07 | 2.52e-08 ± 2.74e-08 | 1.18 | 12.78 ± 0.69 | 10.82 ± 0.58 |
| Promoter_Human.flank | Human_Promoter_Villar.flanking.500 | 3.57 ± 1.06 | -9.98e-04 ± 2.65e-04 | 9.88e-04 ± 2.64e-04 | 9.84e-06 ± 2.42e-06 | 3.06e-07 ± 1.10e-07 | 1.87e-07 ± 1.35e-07 | 0.36 | 5.44 ± 0.6 | 15.09 ± 1.65 |
| Transcr.flank | Transcr_Hoffman.flanking.500 | 0.73 ± 0.02 | 2.22e-04 ± 2.77e-05 | -2.19e-04 ± 2.73e-05 | -2.13e-06 ± 9.56e-07 | -1.18e-07 ± 8.57e-08 | 1.28e-08 ± 1.43e-08 | 41.77 | 47.24 ± 2.69 | 1.13 ± 0.06 |
| MAFbin2 | MAFbin2 | 0.72 ± 0.02 | 1.81e-04 ± 1.14e-04 | -1.83e-04 ± 1.14e-04 | 1.23e-06 ± 1.80e-06 | 3.03e-07 ± 1.22e-07 | 4.66e-08 ± 2.87e-08 | 7.16 | 7.6 ± 0.41 | 1.06 ± 0.06 |
| Repressed.flank | Repressed_Hoffman.flanking.500 | 0.71 ± 0.03 | 7.12e-04 ± 7.85e-05 | -7.08e-04 ± 7.83e-05 | -3.60e-06 ± 1.22e-06 | -1.91e-07 ± 9.82e-08 | -1.31e-08 ± 1.17e-08 | 26.08 | 34.89 ± 3.15 | 1.34 ± 0.12 |
| H3K4me1.flank | H3K4me1_Trynka.flanking.500 | 0.66 ± 0.03 | 3.12e-04 ± 5.81e-05 | -3.19e-04 ± 5.81e-05 | 6.17e-06 ± 1.57e-06 | 3.16e-07 ± 1.52e-07 | 1.65e-08 ± 1.72e-08 | 17.86 | 32.48 ± 3.22 | 1.82 ± 0.18 |
| Repressed | Repressed_Hoffman | 0.58 ± 0.03 | 8.72e-04 ± 6.17e-05 | -8.68e-04 ± 6.16e-05 | -3.92e-06 ± 1.47e-06 | -1.57e-07 ± 1.14e-07 | 7.56e-09 ± 1.28e-08 | 45.24 | 34.44 ± 3.18 | 0.76 ± 0.07 |

## Conversion notes

- Some source pages are available only as linked images; no searchable text is claimed for those pages.

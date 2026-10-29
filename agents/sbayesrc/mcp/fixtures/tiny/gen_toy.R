# Toy dataset generator for SBayesRC MCP testing.
# Produces a small PLINK-1.9 bfile, a per-block LD matrix in the gctb
# "--make-full-ldm" format, a COJO-format GWAS summary, and an annotation
# file, all from a fixed seed so fixtures are reproducible.
# Retained as fixture preparation; scientific computation stays in SBayesRC.
suppressMessages({library(data.table)})

set.seed(20240101)
nSamples   <- 60
nchr       <- 1
nblk       <- 3
snp_per_blk <- c(4L, 6L, 8L)                 # 18 SNPs total
rho        <- 0.35                           # within-block LD correlation

# ---- build block correlation matrices and genotypes -----------------------
snps <- list(); G <- list()
for (b in seq_len(nblk)) {
  m <- snp_per_blk[b]
  S  <- matrix(rho, m, m); diag(S) <- 1
  L  <- chol(S)                              # upper-tri Cholesky
  Z  <- matrix(rnorm(nSamples * m), nrow = nSamples)
  X  <- Z %*% t(L)                           # correlated latent, MxN -> samples x SNPs
  # allele frequencies (minor allele) vary by variant
  p  <- runif(m, 0.2, 0.45)
  ds <- matrix(0, nSamples, m)
  for (s in seq_len(m)) {
    thr0 <- qnorm(p[s]); thr1 <- qnorm(2 * p[s])
    ds[, s] <- ifelse(X[, s] > thr1, 2L, ifelse(X[, s] > thr0, 1L, 0L))
  }
  snps[[b]] <- data.table(CHROM=b, ID=sprintf("rs%04d", 1000*b + seq_len(m)),
                          BP = seq_len(m) + 100000*b, A1="A", A2="G", p=p)
  G[[b]] <- ds
}
dose  <- do.call(cbind, G)
snpDT <- rbindlist(snps)
snpDT[, GenPos := BP/1e6]
snpDT[, A1Freq := 1 - p]                      # A1 = major allele in .bim convention

# ---- write PLINK-1.9 bfile via PED/MAP + plink2 (--make-bed) ---------------
plink2 <- Sys.getenv("P2A_PLINK2", "plink2")
# .map (CHR SNP cM BP)
fwrite(snpDT[, .(CHROM, ID, GenPos, BP)], file="toy_bfile.map", sep="\t", col.names=FALSE, quote=FALSE)
# sample ids
fam <- data.table(FID=sprintf("F%03d", seq_len(nSamples)),
                  IID=sprintf("I%04d", seq_len(nSamples)),
                  PAT=0, MAT=0, SEX=0, PHENO=-9)
fwrite(fam, file="toy_bfile.fam", sep=" ", col.names=FALSE, quote=FALSE)
# .ped: FID IID PAT MAT SEX PHENO + allele pairs (A1=A, A2=G; dosage = #G)
pedcols <- c("FID","IID","PAT","MAT","SEX","PHENO")
famD <- fam[, ..pedcols]
genocells <- lapply(seq_len(ncol(dose)), function(v) {
  d <- dose[, v]
  ifelse(d==0L, "A A", ifelse(d==1L, "A G", "G G"))
})
ped <- as.data.table(cbind(as.matrix(famD), do.call(cbind, genocells)))
fwrite(ped, file="toy_bfile.ped", sep=" ", col.names=FALSE, quote=FALSE)
if (!file.exists(plink2)) stop("plink2 not found: ", plink2)
system2(plink2, c("--ped", "toy_bfile.ped", "--map", "toy_bfile.map",
                  "--make-bed", "--out", "toy_bfile"),
        stdout=TRUE, stderr=TRUE)
# force A1=A, A2=G in the .bim regardless of plink's allele ordering
bim <- fread("toy_bfile.bim")
bim[, V5 := "A"]; bim[, V6 := "G"]
fwrite(bim, file="toy_bfile.bim", sep="\t", col.names=FALSE, quote=FALSE)
for (f in c("toy_bfile.ped", "toy_bfile.map")) if (file.exists(f)) file.remove(f)

# ---- per-block LD matrix in gctb --make-full-ldm format -------------------
# b<block>.ldm.full.bin (float32 m x m) and b<block>.ldm.full.info
dir.create("toyldmtx", showWarnings=FALSE)
for (b in seq_len(nblk)) {
  m   <- snp_per_blk[b]
  R   <- cor(dose[, (if (b==1) 1 else sum(snp_per_blk[1:(b-1)]) + 1):sum(snp_per_blk[1:b]), drop=FALSE])
  con <- file(sprintf("toyldmtx/b%d.ldm.full.bin", b), "wb")
  writeBin(as.numeric(R), con, size=4)          # little-endian float32
  close(con)
  info <- data.table(MarkerIndex=0:(m-1), ID=snpDT[(if (b==1) 1 else sum(snp_per_blk[1:(b-1)])+1):sum(snp_per_blk[1:b]), ID])
  fwrite(info, file=sprintf("toyldmtx/b%d.ldm.full.info", b), sep="\t", quote=FALSE)
}

# ---- GWAS summary (COJO: SNP A1 A2 freq b se p N) -------------------------
# effects: a few causal variants per block, others zero
causal <- c(1L, 2L, 5L, 1L, 3L, 14L)           # per-block causal indices (1-based)
beta  <- rep(0, nrow(snpDT))
for (b in seq_len(nblk)) {
  off  <- if (b==1) 0 else sum(snp_per_blk[1:(b-1)])
  for (ci in causal) {
    idx <- off + ci
    if (idx <= nrow(snpDT)) beta[idx] <- rnorm(1, 0, 0.5)
  }
}
N <- 1000
# marginal b = LD * beta (LD from full dosage correlation) + noise
Rfull <- cor(dose)
ld   <- min(eigen(Rfull)$values)               # nearest-PSD for safety
if (ld < 1e-4) { Rfull <- Rfull + (1e-4 - ld) * diag(nrow(Rfull)) }
bmar <- as.numeric(Rfull %*% beta + rnorm(nrow(snpDT), 0, 0.02))
se   <- sqrt( (1 - bmar^2*runif(nrow(snpDT),0.5,1)) / runif(nrow(snpDT), 0.9, 1.1) ) / sqrt(N)
se   <- pmax(se, 1e-3)
p    <- 2 * pnorm(-abs(bmar/se))
ma   <- data.table(SNP=snpDT$ID, A1="A", A2="G", freq=1-snpDT$p, b=bmar, se=se, p=p, N=N)
fwrite(ma, file="toy.ma", sep="\t", quote=FALSE, na="NA")

# ---- annotation file (SNP Intercept Coding Conserved) ---------------------
annot <- data.table(SNP=snpDT$ID, Intercept=1,
                    Coding=0, Conserved=0)
annot[grepl("rs2[0-9]{3}$|rs1[0-9]{3}[0-9]$", SNP), Coding := 1]   # rough partition
annot[sample.int(nrow(annot), 6), Conserved := 1]
fwrite(annot, file="toy_annot.txt", sep="\t", quote=FALSE, na="NA")

cat("fixture files written:\n")
cat(paste(list.files(pattern="toy_bfile|toy\\.ma|toy_annot|toyldmtx"), collapse="\n"), "\n")
cat(sprintf("samples=%d snps=%d blocks=%d causal=%d\n",
            nSamples, nrow(snpDT), nblk, length(causal)))

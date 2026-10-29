# Build a small SBayesRC LD reference folder ("toyld") in the CURRENT
# working directory from the toy genotype blocks produced by gen_toy.R.
# Only the per-block LD matrices (the data gctb --make-full-ldm would emit)
# are constructed here; eigen decomposition and snp.info merging are done by
# the package's own LDstep3 and LDstep4 functions.
suppressMessages({library(data.table)})
if (!requireNamespace("SBayesRC", quietly=TRUE)) stop("SBayesRC not installed")
library(SBayesRC)

snp_per_blk <- c(4L, 6L, 8L)
nblk <- length(snp_per_blk)
snp_cum <- cumsum(c(0, snp_per_blk))            # 0-based block start offsets

bim <- fread("toy_bfile.bim", header=FALSE)
setnames(bim, c("Chrom","ID","GenPos","PhysPos","A1","A2"))
ma  <- fread("toy.ma")                           # freq = A1(A) frequency
bim <- merge(bim, ma[, .(SNP, freq)], by.x="ID", by.y="SNP", sort=FALSE)
bim[, A1Freq := freq]
bim[, Index := 0:(nrow(bim) - 1L)]

outdir <- "toyld"
if (dir.exists(outdir)) unlink(outdir, recursive=TRUE)
dir.create(outdir)

ldm_rows <- list()
for (b in seq_len(nblk)) {
  m    <- snp_per_blk[b]
  idx0 <- snp_cum[b]
  ids  <- bim$ID[(idx0 + 1L):(idx0 + m)]
  con  <- file(sprintf("toyldmtx/b%d.ldm.full.bin", b), "rb")
  R    <- readBin(con, n=m*m, what=numeric(0), size=4)
  close(con); dim(R) <- c(m, m)
  info <- data.table(Chrom=bim$Chrom[(idx0+1L):(idx0+m)],
                     ID=ids, Index=idx0:(idx0+m-1L),
                     GenPos=bim$GenPos[(idx0+1L):(idx0+m)],
                     PhysPos=bim$PhysPos[(idx0+1L):(idx0+m)],
                     A1=bim$A1[(idx0+1L):(idx0+m)],
                     A2=bim$A2[(idx0+1L):(idx0+m)],
                     A1Freq=bim$A1Freq[(idx0+1L):(idx0+m)],
                     N=seq_len(m) + 1000L)
  fwrite(info, file=sprintf("%s/b%d.ldm.full.info", outdir, b), sep="\t", quote=FALSE, na="NA")
  file.copy(sprintf("toyldmtx/b%d.ldm.full.bin", b),
            sprintf("%s/b%d.ldm.full.bin", outdir, b), overwrite=TRUE)
  ldm_rows[[b]] <- data.table(Block=b, Chrom=1L,
                              StartSnpIdx=idx0, StartSnpID=ids[1],
                              EndSnpIdx=idx0 + m - 1L, EndSnpID=ids[m], NumSnps=m)
}
ldm <- rbindlist(ldm_rows)
fwrite(ldm, file=file.path(outdir, "ldm.info"), sep="\t", quote=FALSE, na="NA")

for (b in seq_len(nblk)) LDstep3(outDir=outdir, blockIndex=b, log2file=FALSE)
LDstep4(outDir=outdir, log2file=FALSE)

cat("toy LD reference built at ", file.path(getwd(), outdir), "\n", sep="")

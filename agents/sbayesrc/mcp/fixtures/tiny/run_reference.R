# End-to-end reference run of the SBayesRC tutorial pipeline on the toy
# dataset. Produces the fixtures and runs tidy -> impute -> sbayesrc ->
# prs -> sbrcMulti, mirroring vignettes/intro.Rmd on small data.
# Usage: Rscript run_reference.R <output_dir>
suppressMessages({library(SBayesRC); library(data.table)})

args  <- commandArgs(trailingOnly=TRUE)
OUT   <- if (length(args) >= 1) args[1] else "."
plink2 <- Sys.getenv("P2A_PLINK2", "plink2")
if (!file.exists(plink2) && Sys.which(basename(plink2)) == "") stop("plink2 not found: ", plink2)

dir.create(OUT, showWarnings=FALSE, recursive=TRUE)
REF <- file.path(OUT, "ref"); dir.create(REF, showWarnings=FALSE)
setwd(REF)
.fa <- commandArgs(FALSE)
HERE <- dirname(normalizePath(sub("^--file=", "", .fa[grep("^--file=", .fa)[1]])))

source(file.path(HERE, "gen_toy.R"))
stopifnot(all(file.exists(c("toy_bfile.bed","toy_bfile.bim","toy_bfile.fam",
                            "toy.ma","toy_annot.txt",
                            sprintf("toyldmtx/b%d.ldm.full.bin", 1:3)))))
source(file.path(HERE, "build_toy_ld.R"))
stopifnot(file.exists("toyld/snp.info"), file.exists("toyld/block1.eigen.bin"))

tidy(mafile="toy.ma", LDdir="toyld", output="toy_tidy", log2file=FALSE)
impute(mafile="toy_tidy", LDdir="toyld", output="toy_imp.ma", log2file=FALSE)
sbayesrc(mafile="toy_imp.ma", LDdir="toyld", outPrefix="toy_sbrc",
         annot="toy_annot.txt", niter=60, burn=20, tuneIter=20, tuneBurn=10,
         outFreq=10, seed=22, log2file=FALSE)

Sys.setenv(PATH=paste(dirname(plink2), Sys.getenv("PATH"), sep=":"))
prs(weight="toy_sbrc.txt", genoPrefix="toy_bfile", outPrefix="toy_prs1",
    tool="plink2", log2file=FALSE)
prs(weight="toy_sbrc.txt", genoPrefix="toy_bfile", outPrefix="toy_prs2",
    tool="plink2", log2file=FALSE)

fam0 <- fread("toy_bfile.fam", header=FALSE)
fwrite(fam0[, .(V1, V2)], file="toy_tune.id", sep=" ", col.names=FALSE, quote=FALSE)
fam0[, V3 := ifelse(seq_len(.N) <= 45, 0L, 1L)]
fwrite(fam0[, .(V1, V2, V3)], file="toy_pheno.txt", sep=" ", col.names=FALSE, quote=FALSE)
sbrcMulti(prs1="toy_prs1.score.txt", prs2="toy_prs2.score.txt",
          outPrefix="toy_multi", tuneid="toy_tune.id",
          pheno="toy_pheno.txt", log2file=FALSE)

cat("REFERENCE PIPELINE COMPLETE in ", REF, "\n", sep="")
cat("weight rows:", nrow(fread("toy_sbrc.txt")), "\n")
par <- fread("toy_sbrc.par")
cat("par hsq estimate (mean):", par[Item=="hsq", Mean][1], "\n")
cat("prs samples:", nrow(fread("toy_prs1.score.txt")), "\n")
cat("multi samples:", nrow(fread("toy_multi.score.txt")), "\n")

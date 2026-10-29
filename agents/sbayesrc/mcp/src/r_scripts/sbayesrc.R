#!/usr/bin/env Rscript
# SBayesRC R backend for the Paper2Agent MCP server.
#
# Contract: Rscript sbayesrc.R <tool> <params.json>
#   - <tool> is one of: tidy, impute, sbayesrc, prs, sbrcMulti, cutLD
#   - <params.json> holds the tool parameters as a JSON object
#   - prints a single JSON result object on stdout:
#       {"status": "ok", "tool": ..., "outputs": [...], "summary": {...}}
#     or {"status": "error", "message": ...}; exits nonzero on error.
#
# Environment:
#   P2A_R_PROJECT  absolute renv project path (defaults to <this>/../../r-runtime)
#   P2A_PLINK2     plink2 binary path used by prs when no explicit tool path given
suppressWarnings(suppressMessages({}))

fullArgs   <- commandArgs(trailingOnly = FALSE)
flagIdx    <- grep("^--file=", fullArgs)
scriptPath <- if (length(flagIdx)) sub("^--file=", "", fullArgs[flagIdx[1]]) else "sbayesrc.R"

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  cat('{"status":"error","message":"usage: sbayesrc.R <tool> <params.json>"}', "\n")
  quit(status = 2)
}
tool       <- args[1]
paramsFile <- args[2]
if (!file.exists(paramsFile)) {
  cat(sprintf('{"status":"error","message":"params file not found: %s"}', paramsFile), "\n")
  quit(status = 2)
}
params <- jsonlite::fromJSON(paramsFile, simplifyVector = FALSE)

# activate the isolated renv project library before loading packages
rproj <- Sys.getenv("P2A_R_PROJECT", "")
if (rproj == "") rproj <- file.path(dirname(normalizePath(scriptPath)), "..", "..", "r-runtime")
if (dir.exists(rproj) && requireNamespace("renv", quietly = TRUE)) {
  renv::load(project = rproj)
}
suppressMessages(library(SBayesRC))
suppressMessages(library(data.table))

# Drop params that are absent (JSON null -> R NULL) so `do.call` never passes
# unused arguments to the SBayesRC functions.
keep_present <- function(p, keys) {
  p[keys][!vapply(p[keys], is.null, logical(1))]
}

result <- tryCatch({
  out <- list()
  switch(tool,
    tidy = {
      mafile     <- params$mafile
      LDdir      <- params$ld_dir
      output     <- params$output
      tbl        <- do.call(tidy, c(list(mafile = mafile, LDdir = LDdir, output = output),
                                    keep_present(params, c("freq_thresh","N_sd_range","rate2pq","log2file"))))
      files <- c(output, paste0(output, ".full"), paste0(output, ".log"))
      out <- list(status = "ok", tool = tool,
                  outputs = files[file.exists(files)],
                  summary = list(n_variants_out = as.integer(nrow(fread(output)))),
                  note = "tidied summary written to output; allele/QC flags in the log")
    },
    impute = {
      mafile      <- params$mafile
      LDdir       <- params$ld_dir
      output      <- params$output
      do.call(impute, c(list(mafile = mafile, LDdir = LDdir, output = output),
                        keep_present(params, c("thresh","log2file"))))
      ma <- fread(output)
      out <- list(status = "ok", tool = tool,
                  outputs = c(output, paste0(output, ".log"))[file.exists(c(output, paste0(output,".log")))],
                  summary = list(n_variants = nrow(ma),
                                 n_imputed = if ("r2" %in% colnames(ma)) sum(ma$r2 == 0, na.rm = TRUE) else 0L),
                  note = "imputed summary written (r2: 0=imputed, 1=typed)")
    },
    sbayesrc = {
      outdir <- dirname(params$out_prefix)
      if (!dir.exists(outdir)) dir.create(outdir, recursive = TRUE, showWarnings = FALSE)
      argsR <- list(mafile = params$mafile, LDdir = params$ld_dir,
                    outPrefix = params$out_prefix)
      if (!is.null(params$annot) && nzchar(params$annot)) argsR$annot <- params$annot
      knobs <- params[c("niter","burn","tuneIter","tuneBurn","seed","outFreq","bOutDetail")]
      knobs <- knobs[!vapply(knobs, is.null, logical(1))]
      do.call(sbayesrc, c(argsR, knobs, list(log2file = FALSE)))
      pref <- params$out_prefix
      suff <- c(".txt",".par",".AnnoPerSnpHsqEnrichment",".AnnoJointProb",".rds",".log")
      outs <- unlist(lapply(suff, function(s) if (file.exists(paste0(pref, s))) paste0(pref, s) else NULL))
      par  <- if (file.exists(paste0(pref, ".par"))) fread(paste0(pref, ".par")) else NULL
      wt   <- if (file.exists(paste0(pref, ".txt"))) fread(paste0(pref, ".txt")) else NULL
      out <- list(status = "ok", tool = tool, outputs = outs,
                  summary = list(n_snps = if (!is.null(wt)) nrow(wt) else 0L,
                                 hsq_mean = if (!is.null(par)) as.numeric(par[Item == "hsq", Mean][1]) else NULL,
                                 nnz_mean = if (!is.null(par)) as.numeric(par[Item == "nnz", Mean][1]) else NULL),
                  note = "weights in <outPrefix>.txt; heritability/architecture in .par; enrichment in .AnnoPerSnpHsqEnrichment")
    },
    prs = {
      pltool <- params$tool
      if (is.null(pltool) || !nzchar(pltool)) pltool <- Sys.getenv("P2A_PLINK2", "plink2")
      do.call(prs, c(list(weight = params$weight, genoPrefix = params$geno_prefix,
                          outPrefix = params$out_prefix, tool = pltool),
                     keep_present(params, c("genoCHR","snplist","keepid","scoreFlag","log2file"))))
      outf <- paste0(params$out_prefix, ".score.txt")
      sc   <- fread(outf)
      out <- list(status = "ok", tool = tool,
                  outputs = c(outf, paste0(params$out_prefix, ".log"))[file.exists(c(outf, paste0(params$out_prefix, ".log")))],
                  summary = list(n_samples = nrow(sc), n_alleles = sum(sc$ALLELE_CT)),
                  note = "PRS in <outPrefix>.score.txt (FID IID ALLELE_CT SCORE)")
    },
    sbrcMulti = {
      do.call(sbrcMulti, c(list(prs1 = params$prs1, prs2 = params$prs2,
                                outPrefix = params$out_prefix,
                                tuneid = params$tuneid, pheno = params$pheno),
                           keep_present(params, c("keepid","log2file"))))
      out <- list(status = "ok", tool = tool,
                  outputs = c(paste0(params$out_prefix, ".score.txt"),
                              paste0(params$out_prefix, ".weight"))[file.exists(c(paste0(params$out_prefix,".score.txt"), paste0(params$out_prefix,".weight")))],
                  summary = list(n_samples = nrow(fread(paste0(params$out_prefix, ".score.txt")))),
                  note = "weighted PRS in <outPrefix>.score.txt; combination weights in .weight")
    },
    cutLD = {
      do.call(cutLD, c(list(inputDir = params$input_ld, outDir = params$output_ld),
                       keep_present(params, c("thresh","log2file"))))
      out <- list(status = "ok", tool = tool,
                  outputs = params$output_ld,
                  summary = list(out_dir = params$output_ld),
                  note = "reduced LD reference written to output_ld")
    },
    {
      out <- list(status = "error", message = paste("unknown tool:", tool))
    }
  )
  out
}, error = function(e) {
  list(status = "error", message = conditionMessage(e))
})

cat(jsonlite::toJSON(result, auto_unbox = TRUE, digits = NA), "\n")
if (!isTRUE(result$status == "ok")) quit(status = 1)

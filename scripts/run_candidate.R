#!/usr/bin/env Rscript
# run_candidate.R
#
# Reads a compiled problem JSON, calls mwTensor::CoupledMWCA,
# and saves the result as JSON + factor matrices as RDS.
#
# Usage:
#   Rscript run_candidate.R <problem.json> <output_dir>
#
# Requires: R >= 4.1, mwTensor, jsonlite, RcppTOML (optional)

library(jsonlite)

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Usage: Rscript run_candidate.R <problem.json> <output_dir>")
}

problem_file <- args[1]
output_dir   <- args[2]

dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

# Read problem definition
problem <- fromJSON(problem_file, simplifyVector = TRUE)
candidate_id <- problem$candidate_id
cat(sprintf("Running candidate: %s\n", candidate_id))

# Load mwTensor
if (!requireNamespace("mwTensor", quietly = TRUE)) {
  stop("mwTensor package is not installed. Install with: remotes::install_github('rikenbit/mwTensor')")
}
library(mwTensor)

# --- Build inputs for CoupledMWCA ---

# Load data arrays from .npy files
# We use RcppCNPy if available, otherwise fall back to a simple reader
load_npy <- function(path) {
  if (requireNamespace("RcppCNPy", quietly = TRUE)) {
    return(RcppCNPy::npyLoad(path))
  }
  # Fallback: read via reticulate
  if (requireNamespace("reticulate", quietly = TRUE)) {
    np <- reticulate::import("numpy")
    return(np$load(path))
  }
  stop(sprintf("Cannot read .npy file: %s. Install RcppCNPy or reticulate.", path))
}

tensors <- problem$tensors
Xs <- list()
for (i in seq_len(nrow(tensors))) {
  t_info <- tensors[i, ]
  arr <- load_npy(t_info$data_file)
  # Ensure correct dimensions
  if (t_info$kind == "matrix") {
    arr <- matrix(arr, nrow = t_info$shape[[1]][1], ncol = t_info$shape[[1]][2])
  }
  Xs[[t_info$id]] <- arr
}

# Build common_model from couplings
# Each coupling group maps a shared factor across blocks.
# common_model format: list(block_id = list(mode_label = factor_label, ...))
couplings <- problem$couplings
common_model <- list()

# Initialize common_model with empty lists for each block
for (i in seq_len(nrow(tensors))) {
  bid <- tensors[i, ]$id
  common_model[[bid]] <- list()
}

# Assign factor labels from mode assignments
mode_assignments <- problem$mode_assignments
for (i in seq_len(nrow(mode_assignments))) {
  ma <- mode_assignments[i, ]
  if (ma$sharing == "common") {
    # Find which coupling group this mode belongs to
    factor_label <- NULL
    for (j in seq_len(nrow(couplings))) {
      members <- couplings[j, ]$members[[1]]
      for (k in seq_len(nrow(members))) {
        if (members[k, ]$block == ma$block && members[k, ]$mode == ma$mode) {
          factor_label <- sprintf("F%d", j)
          break
        }
      }
      if (!is.null(factor_label)) break
    }
    if (!is.null(factor_label)) {
      mode_label <- sprintf("I%d", which(tensors[tensors$id == ma$block, ]$modes[[1]] == ma$mode))
      common_model[[ma$block]][[mode_label]] <- factor_label
    }
  }
}

# For specific modes, assign unique factor labels
specific_counter <- 100
for (i in seq_len(nrow(mode_assignments))) {
  ma <- mode_assignments[i, ]
  if (ma$sharing == "specific" && ma$status == "decompose") {
    mode_label <- sprintf("I%d", which(tensors[tensors$id == ma$block, ]$modes[[1]] == ma$mode))
    if (is.null(common_model[[ma$block]][[mode_label]])) {
      common_model[[ma$block]][[mode_label]] <- sprintf("S%d", specific_counter)
      specific_counter <- specific_counter + 1
    }
  }
}

# Set rank via max_rank
rank <- problem$search$max_rank
if (is.null(rank)) rank <- 3

# Run CoupledMWCA
cat("Setting up CoupledMWCA parameters...\n")
start_time <- proc.time()

tryCatch({
  params <- defaultCoupledMWCAParams(Xs = Xs, common_model = common_model)
  out <- CoupledMWCA(params)

  elapsed <- (proc.time() - start_time)["elapsed"]

  # Extract reconstruction error
  rec_error <- tail(out@common_model@rec_error, 1)
  if (length(rec_error) == 0) rec_error <- NA

  # Save result object
  saveRDS(out, file = file.path(output_dir, "result.rds"))

  # Save summary JSON
  result_summary <- list(
    candidate_id = candidate_id,
    success = TRUE,
    error_message = NULL,
    reconstruction_error = rec_error,
    runtime_seconds = as.numeric(elapsed),
    rank = rank,
    num_tensors = nrow(tensors),
    solver_family = problem$solver$family
  )
  write(toJSON(result_summary, auto_unbox = TRUE, pretty = TRUE),
        file = file.path(output_dir, "result.json"))

  cat(sprintf("Done. Reconstruction error: %f, Time: %.2fs\n", rec_error, elapsed))

}, error = function(e) {
  elapsed <- (proc.time() - start_time)["elapsed"]

  result_summary <- list(
    candidate_id = candidate_id,
    success = FALSE,
    error_message = conditionMessage(e),
    reconstruction_error = NA,
    runtime_seconds = as.numeric(elapsed),
    rank = rank,
    num_tensors = nrow(tensors),
    solver_family = problem$solver$family
  )
  write(toJSON(result_summary, auto_unbox = TRUE, pretty = TRUE),
        file = file.path(output_dir, "result.json"))

  cat(sprintf("FAILED: %s\n", conditionMessage(e)))
})

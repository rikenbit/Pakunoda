#!/usr/bin/env Rscript
# run_candidate.R
#
# Reads a compiled problem JSON, calls mwTensor::CoupledMWCA,
# and saves the result as JSON + RDS.
#
# Usage:
#   Rscript run_candidate.R <problem.json> <output_dir>
#
# Requires: R >= 4.1, mwTensor, jsonlite, RcppCNPy (or reticulate)
#
# Problem JSON fields consumed:
#   tensors[].data_file, id, modes, shape, kind
#   couplings[].members (block, mode)
#   mode_assignments[].block, mode, status, sharing
#   rank                -> all factor dims
#   solver.init_policy  -> initCoupledMWCA
#   solver.seed         -> initCoupledMWCA
#   nested_relations[]  -> ERROR if non-empty
#
# Mapping Pakunoda semantics to mwTensor CoupledMWCAParams:
#
#   mwTensor has two model layers: common_model and specific_model.
#   Pakunoda v0.2 uses ONLY common_model (params@specific = FALSE).
#   All modes (both shared and non-shared) are placed in common_model.
#
#   common_model structure:
#     list(block_id = list(I_label = factor_label, ...))
#     - I_label:  globally unique mode label (I1, I2, I3, ...).
#                 Modes in the same coupling group share the same I_label
#                 because they represent the same entities with identical
#                 dimensions.
#     - factor_label:  identifies the factor matrix.
#                 Shared modes get the same label (F0, F1, ...) -> coupling.
#                 Non-shared decomposed modes get unique labels (S0, S1, ...).
#                 Frozen modes get unique labels (Z0, Z1, ...) and their
#                 common_decomp entry is set to FALSE.
#
#   Rank:
#     params@common_dims[[factor_label]] <- rank  (for ALL factors)
#     params@specific_dims is left at defaults (unused when specific=FALSE).
#
#   Freeze:
#     params@common_decomp[[factor_label]] <- FALSE
#     The factor's initial values (from initCoupledMWCA) are kept fixed.

library(jsonlite)

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) stop("Usage: Rscript run_candidate.R <problem.json> <output_dir>")

problem_file <- args[1]
output_dir   <- args[2]
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

problem <- fromJSON(problem_file, simplifyVector = TRUE)
candidate_id <- problem$candidate_id
cat(sprintf("[Pakunoda] Running candidate: %s\n", candidate_id))

# ---- Reject nested relations ----
if (length(problem$nested_relations) > 0 && nrow(problem$nested_relations) > 0) {
  stop("Nested relations are not yet supported by the solver bridge.")
}

# ---- Load mwTensor ----
if (!requireNamespace("mwTensor", quietly = TRUE)) {
  stop("mwTensor package is not installed.")
}
library(mwTensor)

# ---- Load data ----
load_npy <- function(path) {
  if (requireNamespace("RcppCNPy", quietly = TRUE)) return(RcppCNPy::npyLoad(path))
  if (requireNamespace("reticulate", quietly = TRUE)) return(reticulate::import("numpy")$load(path))
  stop(sprintf("Cannot read .npy: %s. Install RcppCNPy or reticulate.", path))
}

tensors <- problem$tensors
Xs <- list()
for (i in seq_len(nrow(tensors))) {
  t_info <- tensors[i, ]
  arr <- load_npy(t_info$data_file)
  if (t_info$kind == "matrix") {
    arr <- matrix(arr, nrow = t_info$shape[[1]][1], ncol = t_info$shape[[1]][2])
  }
  Xs[[t_info$id]] <- arr
}

# ---- Build common_model ----
# mwTensor requires ALL modes of ALL blocks in common_model.
# Mode labels (I1, I2, ...) must be globally unique.
# Factor labels express sharing: same label = shared factor.

couplings <- problem$couplings
mode_assignments <- problem$mode_assignments

# Step 1: Assign globally unique mode labels (I1, I2, ...)
# and factor labels from couplings + mode_assignments.
mode_label_counter <- 1
# Map "block:mode" -> unique "IN" label
mode_label_map <- list()
# Map "block:mode" -> factor label
factor_label_map <- list()

# First pass: assign factor labels for coupled (shared) modes
if (!is.null(couplings) && nrow(couplings) > 0) {
  for (j in seq_len(nrow(couplings))) {
    members <- couplings[j, ]$members[[1]]
    factor_label <- sprintf("F%d", j - 1)
    # All members of a coupling share the same factor label.
    # Members with the same dimension also share the same mode label (I-label).
    # Determine the shared mode label for this coupling group.
    shared_mode_label <- sprintf("I%d", mode_label_counter)
    mode_label_counter <- mode_label_counter + 1
    for (k in seq_len(nrow(members))) {
      key <- sprintf("%s:%s", members[k, ]$block, members[k, ]$mode)
      factor_label_map[[key]] <- factor_label
      mode_label_map[[key]] <- shared_mode_label
    }
  }
}

# Second pass: assign factor labels for non-shared modes
specific_counter <- 0
frozen_factors <- c()

if (!is.null(mode_assignments) && nrow(mode_assignments) > 0) {
  for (i in seq_len(nrow(mode_assignments))) {
    ma <- mode_assignments[i, ]
    key <- sprintf("%s:%s", ma$block, ma$mode)

    # Skip if already assigned (coupled mode)
    if (!is.null(factor_label_map[[key]])) {
      # Check if frozen
      if (ma$status == "freeze") {
        frozen_factors <- c(frozen_factors, factor_label_map[[key]])
      }
      next
    }

    # Assign unique mode label
    mode_label_map[[key]] <- sprintf("I%d", mode_label_counter)
    mode_label_counter <- mode_label_counter + 1

    if (ma$status == "freeze") {
      factor_label <- sprintf("Z%d", specific_counter)
      frozen_factors <- c(frozen_factors, factor_label)
    } else {
      factor_label <- sprintf("S%d", specific_counter)
    }
    specific_counter <- specific_counter + 1
    factor_label_map[[key]] <- factor_label
  }
}

# Build common_model list
common_model <- list()
for (i in seq_len(nrow(tensors))) {
  bid <- tensors[i, ]$id
  block_modes <- tensors[i, ]$modes[[1]]
  entry <- list()
  for (mode_name in block_modes) {
    key <- sprintf("%s:%s", bid, mode_name)
    ml <- mode_label_map[[key]]
    fl <- factor_label_map[[key]]
    if (is.null(ml) || is.null(fl)) {
      stop(sprintf("Mode '%s' in block '%s' has no label assignment. Check mode_assignments.", mode_name, bid))
    }
    entry[[ml]] <- fl
  }
  common_model[[bid]] <- entry
}

cat(sprintf("[Pakunoda] common_model built: %d blocks, %d mode labels\n",
            length(common_model), mode_label_counter - 1))

# ---- Solver settings ----
rank <- problem$rank
if (is.null(rank)) rank <- problem$search$max_rank
if (is.null(rank)) rank <- 2L
rank <- as.integer(rank)

init_policy <- problem$solver$init_policy
if (is.null(init_policy)) init_policy <- "random"

solver_seed <- problem$solver$seed

cat(sprintf("[Pakunoda] Rank: %d, Init: %s\n", rank, init_policy))

# ---- Run CoupledMWCA ----
start_time <- proc.time()

tryCatch({
  params <- defaultCoupledMWCAParams(Xs = Xs, common_model = common_model)

  # Fix: defaultCoupledMWCAParams generates mask/weights with names "X1","X2",...
  # but Xs may have custom names (e.g. "expression","methylation").
  # Align mask and weights names to match Xs.
  names(params@mask) <- names(params@Xs)
  names(params@weights) <- names(params@Xs)

  # --- Rank: set dims for all common factors ---
  # In Pakunoda v0.2, all factors (shared and non-shared) live in common_model.
  # params@specific is FALSE (we don't use mwTensor's specific_model layer),
  # so specific_dims/specific_decomp are irrelevant and left at defaults.
  # common_dims controls the number of components for every factor.
  for (fname in names(params@common_dims)) {
    params@common_dims[[fname]] <- rank
  }

  # --- Freeze: set decomp=FALSE for frozen factors ---
  # A frozen factor's initial values are kept fixed during optimization.
  # Since all factors are in common_model, we only need common_decomp.
  if (length(frozen_factors) > 0) {
    cat(sprintf("[Pakunoda] Freezing factors: %s\n", paste(frozen_factors, collapse = ", ")))
    for (fname in frozen_factors) {
      if (fname %in% names(params@common_decomp)) {
        params@common_decomp[[fname]] <- FALSE
      } else {
        warning(sprintf("Frozen factor '%s' not found in common_decomp; ignoring.", fname))
      }
    }
  }

  # Initialize and run
  init <- initCoupledMWCA(params, seed = solver_seed, init_policy = init_policy)
  out <- CoupledMWCA(init)
  elapsed <- (proc.time() - start_time)["elapsed"]

  rec_error <- tail(out@rec_error, 1)
  if (length(rec_error) == 0) rec_error <- NA

  saveRDS(out, file = file.path(output_dir, "result.rds"))

  result <- list(
    candidate_id = candidate_id,
    success = TRUE,
    error_message = NULL,
    reconstruction_error = rec_error,
    runtime_seconds = as.numeric(elapsed),
    rank = rank,
    init_policy = init_policy,
    num_tensors = nrow(tensors),
    num_frozen_factors = length(frozen_factors),
    solver_family = problem$solver$family
  )
  write(toJSON(result, auto_unbox = TRUE, pretty = TRUE),
        file = file.path(output_dir, "result.json"))
  cat(sprintf("[Pakunoda] Done. rec_error: %f, time: %.2fs\n", rec_error, elapsed))

}, error = function(e) {
  elapsed <- (proc.time() - start_time)["elapsed"]
  result <- list(
    candidate_id = candidate_id,
    success = FALSE,
    error_message = conditionMessage(e),
    reconstruction_error = NA,
    runtime_seconds = as.numeric(elapsed),
    rank = rank,
    init_policy = init_policy,
    num_tensors = nrow(tensors),
    num_frozen_factors = length(frozen_factors),
    solver_family = problem$solver$family
  )
  write(toJSON(result, auto_unbox = TRUE, pretty = TRUE),
        file = file.path(output_dir, "result.json"))
  cat(sprintf("[Pakunoda] FAILED: %s\n", conditionMessage(e)))
})

#' Subject separation helpers
#'
#' @description
#' Internal helpers behind the `subject_sep` argument of `pre_process()`. A
#' dataset may hold the time series of several subjects side by side (for
#' example cheese A in `A_1..A_5` and cheese C in `C_1..C_5`). The parsed
#' description is a data frame with one row per time column:
#' `column` (column name), `subject` (subject name) and `time` (the label of
#' that column on the time axis shared by all subjects). It is stored on the
#' processed data as `attr(data, "subject_sep")`.
#'
#' @param subject_sep A named list of column names, or a string such as
#'   `"A:A_1-A_5;C:C_1-C_5"`. See `pre_process()`.
#' @param data The data frame whose columns are described.
#'
#' @return `parse_subject_sep__()` returns the map data frame.
#' @keywords internal
#' @noRd
parse_subject_sep__ <- function(subject_sep, data) {
  cols <- colnames(data)

  if (is.character(subject_sep) && is.null(names(subject_sep))) {
    parts <- trimws(unlist(strsplit(paste(subject_sep, collapse = ";"), ";", fixed = TRUE)))
    parts <- parts[nzchar(parts)]
    pos <- regexpr(":", parts, fixed = TRUE)
    if (!length(parts) || any(pos < 2)) {
      stop("`subject_sep` must look like \"A:A_1-A_5;C:C_1-C_5\".")
    }
    spec <- strsplit(substring(parts, pos + 1), ",", fixed = TRUE)
    names(spec) <- trimws(substring(parts, 1, pos - 1))
  } else if (is.list(subject_sep) && !is.null(names(subject_sep)) && all(nzchar(names(subject_sep)))) {
    spec <- lapply(subject_sep, as.character)
  } else {
    stop("`subject_sep` must be a named list of column names or a string like \"A:A_1-A_5;C:C_1-C_5\".")
  }
  if (anyDuplicated(names(spec))) stop("`subject_sep` names each subject once.")

  groups <- lapply(spec, function(tokens) {
    unlist(lapply(trimws(tokens), expand_subject_token__, cols = cols))
  })

  all_cols <- unlist(groups, use.names = FALSE)
  if (anyDuplicated(all_cols)) {
    stop("`subject_sep` assigns a column to more than one subject: ",
         paste(unique(all_cols[duplicated(all_cols)]), collapse = ", "))
  }
  if (any(lengths(groups) < 2)) {
    stop("Every subject in `subject_sep` needs at least two time columns.")
  }
  missed <- setdiff(cols, c("ID", "type", all_cols))
  if (length(missed)) {
    stop("`subject_sep` does not cover these columns: ", paste(missed, collapse = ", "))
  }

  time <- unlist(lapply(names(groups), function(s) subject_time_labels__(groups[[s]], s)),
                 use.names = FALSE)
  data.frame(
    column = all_cols,
    subject = rep(names(groups), lengths(groups)),
    time = time,
    stringsAsFactors = FALSE
  )
}

# One token of the string form: a column name, or a positional range "x-y".
expand_subject_token__ <- function(token, cols) {
  if (token %in% cols) return(token)
  dash <- gregexpr("-", token, fixed = TRUE)[[1]]
  for (d in dash[dash > 0]) {
    from <- trimws(substring(token, 1, d - 1))
    to <- trimws(substring(token, d + 1))
    if (from %in% cols && to %in% cols) {
      return(cols[match(from, cols):match(to, cols)])
    }
  }
  stop("`subject_sep` refers to an unknown column or range: ", token)
}

# Time labels of one subject: the column name without the subject prefix
# ("A_1" -> "1"), or the position when the names do not follow that pattern.
subject_time_labels__ <- function(columns, subject) {
  prefixed <- startsWith(columns, subject)
  labels <- sub("^[_.-]", "", substring(columns, nchar(subject) + 1))
  if (!all(prefixed) || any(!nzchar(labels)) || anyDuplicated(labels)) {
    labels <- as.character(seq_along(columns))
  }
  labels
}

# Levels of the shared time axis: numeric order when possible.
subject_time_levels__ <- function(map) {
  labels <- unique(map$time)
  num <- suppressWarnings(as.numeric(labels))
  if (!anyNA(num)) labels <- labels[order(num)]
  labels
}

# The map logged by pre_process(), or NULL when absent or out of date.
get_subject_map__ <- function(data) {
  map <- attr(data, "subject_sep")
  if (!is.data.frame(map) || !all(c("column", "subject", "time") %in% colnames(map))) {
    return(NULL)
  }
  if (!all(map$column %in% colnames(data))) return(NULL)
  map
}

# Scale every row within each subject. A subject in which the row is flat has
# no pattern: it is set to 0, and rows that are flat in every subject are
# dropped.
scale_subjects__ <- function(data, map) {
  groups <- split(map$column, factor(map$subject, levels = unique(map$subject)))
  data <- scale_by_row__(data, groups)
  flat <- is.nan(as.matrix(as.data.frame(data)[, map$column, drop = FALSE]))
  for (col in map$column) {
    data[[col]][flat[, col]] <- 0
  }
  data[rowSums(flat) < ncol(flat), , drop = FALSE]
}

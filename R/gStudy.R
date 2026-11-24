#' Describe the study behind the data
#'
#' @description
#' `gStudy()` is written once, before anything else. It says which columns of
#' the data are what, and what they mean. `pre_process()`, `gAnnotation()` and
#' `gDashboard_d3()` read it, so the same facts are not repeated in each call,
#' and the dashboard and the MolPad agent get the words of your study instead
#' of generic ones.
#'
#' @param background One or two sentences about the study.
#' @param feature Optional. What one row of the data is called, e.g.
#'   `"contig"`, so that the agent reads "which contigs ..." as a question about
#'   rows. Without it the word "feature" is used.
#' @param samples How the value columns relate to each other. A list with
#'   * `groups`: one sentence on the sample groups, e.g. "Two kinds of cheese,
#'     A and C.". A note per group is possible but not needed:
#'     `list(A = "cheese A", C = "cheese C")`;
#'   * `time`: one sentence on the time points, e.g. "Sampling time points
#'     during ripening, aligned between the cheeses but with missing ones.";
#'   * `columns`: which columns belong to which group, written as for the
#'     `subject_sep` argument of [pre_process()]. Leave it out when the column
#'     names say it: `A_1, A_2, C_1, C_2` is read as groups `A` and `C` (the
#'     text before the last `_`, `.` or `-`), with the number as the time.
#' @param level1,level2 The two annotation columns the dashboard filters on:
#'   the column name, e.g. `"phylum"`, or
#'   `list(column = "phylum", name = "phylum", about = "the phylum a contig is
#'   assigned to")`. Level 1 is the main tag; level 2 is either a finer part
#'   of it (phylum > class) or another kind of tag (function x taxonomy), which
#'   is read from the data.
#' @param colour The column that colours the lines of the pattern plot by
#'   default (the `type` column of the processed data), e.g. `"phylum"`.
#' @param ids Annotation columns that hold database ids and their database,
#'   e.g. `c(GO_ID = "GO", KEGG_ID = "KEGG")`.
#' @param missing The text that stands for "no annotation" in the id columns.
#' @param file Read the study from a JSON file written by [write_study()]
#'   instead; the other arguments are then not used.
#'
#' @return An object of class `molpad_study` (a list).
#'
#' @examples
#' study <- gStudy(
#'   background = "Metagenomes of two washed-rind cheeses over ripening.",
#'   feature = "contig",
#'   samples = list(groups = "Two kinds of cheese, A and C.",
#'                  time = "Sampling time points during ripening, aligned but with missing ones."),
#'   level1 = "phylum", level2 = "class", colour = "phylum",
#'   ids = c(GO_ID = "GO", KEGG_ID = "KEGG"))
#' study
#'
#' @export
gStudy <- function(background = NULL, feature = NULL, samples = NULL,
                   level1 = NULL, level2 = NULL, colour = NULL, ids = NULL,
                   missing = NULL, file = NULL) {
  if (!is.null(file)) {
    x <- jsonlite::fromJSON(file, simplifyVector = FALSE)
  } else {
    x <- list(background = background, feature = feature, samples = samples,
              level1 = level1, level2 = level2, colour = colour, ids = ids, missing = missing)
  }
  as_study__(x)
}

#' Save a study to a JSON file
#'
#' The file can be read back with `gStudy(file = )`, and given to the MolPad
#' agent as its `--context`.
#' @param study The output of [gStudy()].
#' @param file Path of the JSON file.
#' @return `file`, invisibly.
#' @export
write_study <- function(study, file) {
  study <- as_study__(study)
  writeLines(jsonlite::toJSON(unclass(study), auto_unbox = TRUE, pretty = TRUE, null = "null"), file)
  invisible(file)
}

#' @export
print.molpad_study <- function(x, ...) {
  line <- function(label, text) if (!is.null(text)) cat(sprintf("%-11s %s\n", label, text))
  cat("MolPad study\n")
  line("background", x$background)
  line("feature", x$feature$name)
  s <- x$samples
  if (is.character(s$groups)) line("groups", s$groups)
  else for (g in names(s$groups)) line(paste0("group ", g), s$groups[[g]])
  when <- c(s$time$about, if (!is.null(s$time$unit)) paste0("unit: ", s$time$unit))
  if (length(when)) line("time", paste(when, collapse = "; "))
  if (!is.null(s$columns)) line("columns", "given")
  for (key in c("level1", "level2", "colour")) {
    e <- x[[key]]
    if (length(e)) line(key, paste(c(e$column, if (!identical(e$name, e$column)) e$name, e$about), collapse = " | "))
  }
  if (length(x$ids)) line("ids", paste(names(x$ids), vapply(x$ids, function(i) i$type, ""), sep = " = ", collapse = ", "))
  line("missing", x$missing)
  invisible(x)
}

# ---- internal ---------------------------------------------------------------

study_keys__ <- c("background", "feature", "samples", "level1", "level2", "colour", "ids", "missing")

# NULL, a study, a plain list with the same entries, or the path of a JSON file -> a study (or NULL).
as_study__ <- function(x) {
  if (is.null(x)) return(NULL)
  if (inherits(x, "molpad_study")) return(x)
  if (is.character(x) && length(x) == 1 && is.null(names(x)) && file.exists(x)) {
    x <- jsonlite::fromJSON(x, simplifyVector = FALSE)
  }
  if (!is.list(x) || (length(x) && is.null(names(x)))) {
    stop("A study is the output of gStudy(), a named list with the same entries, or the path of its JSON file.")
  }
  bad <- setdiff(names(x), study_keys__)
  if (length(bad)) {
    stop("Unknown entries in the study: ", paste(bad, collapse = ", "),
         ". Allowed: ", paste(study_keys__, collapse = ", "), ".")
  }
  compact <- function(l) l[!vapply(l, is.null, logical(1))]
  # "phylum" is short for list(<short> = "phylum")
  entry <- function(v, short) {
    if (is.null(v)) return(NULL)
    if (is.character(v) && is.null(names(v))) return(stats::setNames(list(v[1]), short))
    as.list(v)
  }
  level <- function(v) {
    v <- entry(v, "column")
    if (is.null(v)) return(NULL)
    if (is.null(v$name)) v$name <- v$column
    v
  }
  samples <- NULL
  if (!is.null(x$samples)) {
    samples <- entry(x$samples, "groups")
    bad <- setdiff(names(samples), c("groups", "time", "columns"))
    if (length(bad)) {
      stop("Unknown entries in `samples`: ", paste(bad, collapse = ", "),
           ". Allowed: groups, time, columns.")
    }
    # one sentence for all groups, or a note per group
    g <- samples$groups
    if (!is.null(g)) {
      samples$groups <- if (is.null(names(g))) paste(as.character(unlist(g)), collapse = " ")
                        else lapply(as.list(g), as.character)
    }
    samples$time <- entry(samples$time, "about")
  }
  ids <- NULL
  if (length(x$ids)) {
    ids <- lapply(as.list(x$ids), function(v) entry(v, "type"))
    if (is.null(names(ids)) || !all(nzchar(names(ids)))) {
      stop("`ids` names the id columns, e.g. c(GO_ID = \"GO\", KEGG_ID = \"KEGG\").")
    }
  }
  out <- compact(list(
    background = if (!is.null(x$background)) paste(as.character(x$background), collapse = " "),
    feature = entry(x$feature, "name"),
    samples = if (length(samples)) compact(samples),
    level1 = level(x$level1),
    level2 = level(x$level2),
    colour = level(x$colour),
    ids = ids,
    missing = if (!is.null(x$missing)) as.character(x$missing)[1]
  ))
  structure(out, class = "molpad_study")
}

# The study a processed object carries (pre_process() and gAnnotation() attach it).
get_study__ <- function(...) {
  for (x in list(...)) {
    s <- attr(x, "molpad_study")
    if (inherits(s, "molpad_study")) return(s)
  }
  NULL
}

# Sample groups read from the column names: "A_1, A_2, C_1" -> list(A = c("A_1", "A_2"), C = "C_1").
# NULL unless every column ends in a number after a separator and there are at least two
# groups of at least two columns.
detect_subjects__ <- function(columns) {
  m <- regmatches(columns, regexec("^(.+)[_.-]([0-9]+(?:\\.[0-9]+)?)$", columns, perl = TRUE))
  if (!length(columns) || any(lengths(m) != 3)) return(NULL)
  group <- vapply(m, function(v) v[2], character(1))
  groups <- split(columns, factor(group, levels = unique(group)))
  if (length(groups) < 2 || any(lengths(groups) < 2)) return(NULL)
  # the columns of a group must lie next to each other, as subject_sep expects
  if (!identical(unname(unlist(groups)), columns)) return(NULL)
  lapply(groups, as.character)
}

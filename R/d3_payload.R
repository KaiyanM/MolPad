#' Build the data payload for the D3 dashboard
#'
#' @description
#' Internal helpers that turn the four `gDashboard()` inputs into the plain
#' list that `gDashboard_d3()` serialises to JSON. The JSON contract is
#' documented in `inst/d3dashboard/SCHEMA.md`; anything that writes the same
#' structure (for example a Python script) can drive the same front end.
#'
#' @param data The output of `pre_process()`: `ID`, time columns, `type`.
#' @param cluster The output of `gClusters()`.
#' @param annotation The output of `gAnnotation()`.
#' @param networkres The output of `gNetwork()`.
#' @param dashboardtitle Title shown in the page header.
#' @param id_colname,id_type Annotation columns holding database ids and
#'   their database type (`"GO"` or `"KEGG"`), as in `gDashboard()`.
#' @param study The output of [gStudy()]; by default the one given to
#'   `pre_process()` or `gAnnotation()`.
#'
#' @return A named list ready for [d3_payload_json()].
#' @keywords internal
#' @noRd
d3_payload <- function(data, cluster, annotation, networkres,
                       dashboardtitle = "MolPad Dashboard",
                       id_colname = NULL, id_type = NULL, study = NULL) {
  subject_map <- get_subject_map__(data)
  level_sources <- attr(annotation, "molpad_levels")
  study <- as_study__(study)
  if (is.null(study)) study <- get_study__(data, annotation)
  if (is.null(id_colname) && is.null(id_type) && length(study$ids)) {
    id_colname <- names(study$ids)
    id_type <- vapply(study$ids, function(i) as.character(i$type), character(1), USE.NAMES = FALSE)
  }
  data <- as.data.frame(data)
  annotation <- as.data.frame(annotation)
  networkres <- as.data.frame(networkres)

  # ---- validation -----------------------------------------------------------
  for (col in c("ID", "type")) {
    if (!col %in% colnames(data)) stop("`data` must contain a column named `", col, "`.")
  }
  for (col in c("ID", "Pathway", "taxonomic.scope")) {
    if (!col %in% colnames(annotation)) stop("`annotation` must contain a column named `", col, "`.")
  }
  for (col in c("weight", "var_names", "from")) {
    if (!col %in% colnames(networkres)) stop("`networkres` must contain a column named `", col, "`.")
  }
  if (!is.list(cluster) || is.null(cluster[[1]]$cluster)) {
    stop("`cluster` must be the output of gClusters() (a list whose first element is a kmeans object).")
  }
  if (length(cluster[[1]]$cluster) != nrow(data)) {
    stop("`cluster[[1]]$cluster` must have one entry per row of `data`.")
  }
  if (ncol(data) < 3) stop("`data` needs at least one time column between `ID` and `type`.")

  # ---- time points: every column between ID (first) and type (last) ---------
  timepoints <- colnames(data)[-c(1, ncol(data))]

  # ---- subjects: groups of time columns drawn as separate ribbon facets ------
  if (is.null(subject_map)) {
    subjects <- list()
    time_labels <- timepoints
  } else {
    subjects <- lapply(unique(subject_map$subject), function(s) {
      rows <- subject_map$subject == s
      list(name = s, columns = I(subject_map$column[rows]), labels = I(subject_map$time[rows]))
    })
    time_labels <- subject_time_levels__(subject_map)
  }

  # ---- per-feature table: cluster labels + annotation columns ---------------
  graphptw <- reshape_for_make_functions(data, cluster, annotation, NULL, NULL)$output_graphptw
  annotation_columns <- setdiff(colnames(annotation), "ID")
  ord <- match(data$ID, graphptw$ID)

  values <- as.matrix(data[, timepoints, drop = FALSE])
  storage.mode(values) <- "double"
  features <- data.frame(
    ID = as.character(data$ID),
    cluster = graphptw$cluster[ord],
    type = as.character(data$type),
    stringsAsFactors = FALSE
  )
  features$values <- lapply(seq_len(nrow(values)), function(i) unname(values[i, ]))
  for (col in annotation_columns) {
    v <- graphptw[[col]][ord]
    features[[col]] <- if (is.factor(v)) as.character(v) else v
  }

  # ---- edges: raw gNetwork rows, NaN -> NA (serialised as null) -------------
  edges <- data.frame(
    from = as.character(networkres$from),
    to = as.character(networkres$var_names),
    weight = as.numeric(networkres$weight),
    stringsAsFactors = FALSE
  )
  edges$weight[is.nan(edges$weight)] <- NA_real_
  if ("IncNodePurity" %in% colnames(networkres)) {
    edges$IncNodePurity <- as.numeric(networkres$IncNodePurity)
    edges$IncNodePurity[is.nan(edges$IncNodePurity)] <- NA_real_
  }

  clusters <- d3_sort_clusters(unique(c(features$cluster, edges$from, edges$to)))

  # ---- slider defaults, identical to gDashboard() ---------------------------
  q <- stats::quantile(abs(edges$weight), na.rm = TRUE)
  weight_slider <- list(
    min = 0,
    max = round(unname(q[4]), 1),
    value = round(unname(q[3]), 1),
    step = 0.1
  )
  if (!is.finite(weight_slider$max)) weight_slider$max <- 1
  if (!is.finite(weight_slider$value)) weight_slider$value <- 0
  weight_slider$max <- max(weight_slider$max, weight_slider$step)

  id_links <- d3_link_templates(id_colname, id_type)
  dataset <- d3_dataset(study, features, id_links, level_sources,
                        vapply(subjects, function(s) s$name, character(1)))

  list(
    schema_version = 2L,
    title = as.character(dashboardtitle)[1],
    timepoints = I(timepoints),
    subjects = subjects,
    time_labels = I(time_labels),
    types = I(d3_unique_chr(data$type)),
    taxa = I(d3_unique_chr(annotation$taxonomic.scope)),
    pathways = I(d3_unique_chr(annotation$Pathway)),
    clusters = I(clusters),
    annotation_columns = I(annotation_columns),
    id_links = id_links,
    dataset = dataset,
    features = features,
    edges = edges,
    weight_slider = weight_slider
  )
}

#' The description of the dataset written into the page (`dataset` in SCHEMA.md)
#'
#' The study says what cannot be computed; the rest is read from the data: how
#' level 2 relates to level 1, whether the colour column repeats a level, and
#' what the ids look like.
#' @keywords internal
#' @noRd
d3_dataset <- function(study, features, id_links, level_sources = NULL,
                       subject_names = character(0)) {
  study <- as_study__(study)
  compact <- function(x) x[!vapply(x, is.null, logical(1))]
  first <- function(...) {
    for (v in list(...)) if (!is.null(v) && !is.na(v) && nzchar(v)) return(v)
    NULL
  }

  placeholders <- c("Unknown", "Other", "-", "", NA)   # written by gAnnotation() / pre_process()
  l1 <- as.character(features$Pathway)
  l2 <- as.character(features$taxonomic.scope)
  ty <- as.character(features$type)

  # "column" is the fixed name in the page; "source" what the user's column was called
  level <- function(key, column) {
    x <- study[[key]]
    source <- first(x$column, level_sources[[key]])
    compact(c(list(column = column, source = source, name = first(x$name, source)),
              x[setdiff(names(x), c("column", "source", "name"))]))
  }
  level1 <- level("level1", "Pathway")
  level2 <- level("level2", "taxonomic.scope")
  if (is.null(level2$relation)) {
    # nested: every level-2 value sits under one level-1 value; crossed: another kind of tag
    keep <- !(l1 %in% placeholders) & !(l2 %in% placeholders)
    parents <- tapply(l1[keep], l2[keep], function(v) length(unique(v)))
    level2$relation <- if (length(parents) && all(parents == 1)) "nested" else "crossed"
  } else if (!level2$relation %in% c("nested", "crossed")) {
    stop("`level2$relation` of the study must be \"nested\" or \"crossed\".")
  }

  colour <- level("colour", "type")
  if (is.null(colour$same_as)) {
    same <- function(v) {
      keep <- !(ty %in% placeholders) & !(v %in% placeholders)
      any(keep) && all(ty[keep] == v[keep])
    }
    colour$same_as <- if (same(l1)) "level1" else if (same(l2)) "level2" else NULL
  }
  if (is.null(colour$name) && !is.null(colour$same_as)) {
    colour$name <- list(level1 = level1, level2 = level2)[[colour$same_as]]$name
  }

  id_names <- c(KEGG = "KEGG ortholog id", GO = "GO term id")
  ids <- lapply(names(id_links), function(col) {
    link <- id_links[[col]]
    cells <- as.character(features[[col]])
    hit <- regmatches(cells, regexpr(paste0("[^,;[:space:]]*", link$pattern), cells, perl = TRUE))
    example <- if (length(hit)) regmatches(hit[1], regexpr(link$pattern, hit[1], perl = TRUE)) else NULL
    prefix <- if (length(hit)) sub(example, "", hit[1], fixed = TRUE) else ""
    x <- study$ids[[col]]
    compact(c(list(type = link$type, name = first(x$name, unname(id_names[link$type])),
                   example = example, prefix = if (nzchar(prefix)) prefix else NULL),
              x[setdiff(names(x), c("type", "name", "example", "prefix"))]))
  })
  ids <- stats::setNames(ids, names(id_links))

  samples <- study$samples[setdiff(names(study$samples), "columns")]   # the columns are in "subjects"
  unknown <- if (is.list(samples$groups)) setdiff(names(samples$groups), subject_names) else character(0)
  if (length(unknown)) {
    stop("`samples$groups` of the study names sample groups that are not in the data: ",
         paste(unknown, collapse = ", "), ". The data has: ",
         if (length(subject_names)) paste(subject_names, collapse = ", ") else "no sample groups", ".")
  }
  missing <- study$missing
  if (is.null(missing)) {
    cells <- unlist(lapply(names(id_links), function(col) as.character(features[[col]])))
    if (any(cells == "-", na.rm = TRUE)) missing <- "-"
  }

  compact(list(
    background = study$background,
    feature = study$feature,
    level1 = level1,
    level2 = level2,
    colour = colour,
    ids = if (length(ids)) ids else NULL,
    samples = if (length(samples)) samples else NULL,
    missing = missing
  ))
}

#' Link templates for database id columns
#'
#' Mirrors the regular expressions and URLs used by [paste_URL()], but hands
#' them to the browser instead of rendering HTML in R.
#' @keywords internal
#' @noRd
d3_link_templates <- function(id_colname = NULL, id_type = NULL) {
  if (is.null(id_colname) || is.null(id_type)) {
    return(stats::setNames(list(), character(0)))
  }
  if (length(id_colname) != length(id_type)) {
    stop("`id_colname` and `id_type` must have the same length.")
  }
  known <- list(
    KEGG = list(pattern = "K\\d{5}", url = "https://www.kegg.jp/entry/{id}"),
    GO = list(pattern = "GO:\\d{7}", url = "https://www.ebi.ac.uk/QuickGO/term/{id}")
  )
  bad <- setdiff(id_type, names(known))
  if (length(bad)) {
    stop("`id_type` must be one of: ", paste(names(known), collapse = ", "),
         ". Unknown: ", paste(bad, collapse = ", "))
  }
  out <- lapply(seq_along(id_colname), function(i) {
    c(list(type = id_type[i]), known[[id_type[i]]])
  })
  stats::setNames(out, id_colname)
}

#' Serialise the payload to a JSON string safe for a `<script>` tag
#' @keywords internal
#' @noRd
d3_payload_json <- function(payload) {
  json <- jsonlite::toJSON(
    payload,
    auto_unbox = TRUE, dataframe = "rows", na = "null", null = "null",
    digits = 8, pretty = FALSE
  )
  # "</" may never appear inside an inline <script>; "<\/" is a legal JSON escape.
  gsub("</", "<\\/", as.character(json), fixed = TRUE)
}

d3_unique_chr <- function(x) {
  x <- unique(as.character(x))
  x[!is.na(x)]
}

d3_sort_clusters <- function(x) {
  x <- unique(as.character(x))
  x <- x[!is.na(x)]
  num <- suppressWarnings(as.numeric(sub("^.*?(\\d+)$", "\\1", x)))
  x[order(is.na(num), num, x)]
}

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
#'
#' @return A named list ready for [d3_payload_json()].
#' @keywords internal
#' @noRd
d3_payload <- function(data, cluster, annotation, networkres,
                       dashboardtitle = "MolPad Dashboard",
                       id_colname = NULL, id_type = NULL) {
  subject_map <- get_subject_map__(data)
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
    id_links = d3_link_templates(id_colname, id_type),
    features = features,
    edges = edges,
    weight_slider = weight_slider
  )
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

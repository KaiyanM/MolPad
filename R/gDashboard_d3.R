#' Generate a static D3.js dashboard
#'
#' @description
#' `gDashboard_d3()` builds the same dashboard as [gDashboard()] but as a
#' static HTML page rendered with D3.js. No Shiny server is needed: R only
#' serialises the inputs to JSON and assembles the page from the files in
#' `inst/d3dashboard/`, so the result can be opened from disk, emailed, or
#' hosted on any static web server.
#'
#' @details
#' The page contains three linked views and an annotation table:
#'
#' * a cluster network whose nodes are coloured by the number of features
#'   carrying the selected functional annotation (`Pathway`), with a weight
#'   slider for the edges, force/circle/grid layouts and draggable nodes;
#' * a stacked bar chart of taxonomic scope per selected cluster;
#' * a ribbon plot of min/mean/max expression per `type` over time, one panel
#'   per selected cluster;
#' * a searchable, sortable table of the selected features, with a sort and
#'   filter menu on every column header. Columns listed in
#'   `id_colname` are rendered as links to the database named in `id_type`.
#'
#' Clusters are selected by brushing a rectangle on the network or by clicking
#' nodes. All clusters are selected when nothing is brushed.
#'
#' All filtering and aggregation happens in the browser. The JSON contract
#' between R and the page is documented in
#' `system.file("d3dashboard", "SCHEMA.md", package = "MolPad")`, so another
#' language can produce the same page by writing the same JSON.
#'
#' @param data The output of `pre_process()`: a data.frame with `ID` first,
#'   one column per time point, and `type` last.
#' @param cluster The output of `gClusters()`.
#' @param annotation The output of `gAnnotation()`: a data.frame containing
#'   `ID`, `Pathway` and `taxonomic.scope` plus any further annotation columns.
#' @param networkres The output of `gNetwork()`.
#' @param dashboardtitle Title shown in the page header and browser tab.
#' @param id_colname Names of annotation columns holding database ids, or
#'   `NULL` for no links.
#' @param id_type Database for each column in `id_colname`: `"GO"` or `"KEGG"`.
#' @param output_dir Directory the page is written to. Created if missing.
#'   Defaults to a fresh folder under [tempdir()].
#' @param file_name Name of the HTML file inside `output_dir`.
#' @param self_contained If `TRUE` (default) the CSS, D3 and dashboard scripts
#'   are inlined into a single HTML file. If `FALSE` they are copied next to
#'   the page as `css/`, `lib/` and `js/` folders, which is convenient for
#'   editing the JavaScript.
#' @param open If `TRUE` the page is opened with `viewer` after writing.
#' @param viewer Function used to open the page. Defaults to the RStudio
#'   viewer when available and to [utils::browseURL()] otherwise.
#'
#' @return The path to the written HTML file, invisibly.
#'
#' @examples
#' \dontrun{
#' data(test_data)
#' gDashboard_d3(test_data_processed, test_cluster, test_annotations_processed,
#'               test_network, dashboardtitle = "Test",
#'               id_colname = c("GO_ID", "KEGG_ID"), id_type = c("GO", "KEGG"))
#' }
#'
#' @importFrom jsonlite toJSON fromJSON
#' @importFrom utils browseURL
#' @importFrom stats quantile setNames
#' @export
gDashboard_d3 <- function(data, cluster, annotation, networkres,
                          dashboardtitle = "MolPad Dashboard",
                          id_colname = NULL, id_type = NULL,
                          output_dir = tempfile("molpad_d3_"),
                          file_name = "index.html",
                          self_contained = TRUE,
                          open = interactive(),
                          viewer = getOption("viewer", utils::browseURL)) {
  payload <- d3_payload(data, cluster, annotation, networkres,
                        dashboardtitle, id_colname, id_type)
  path <- d3_render_html(payload, output_dir, file_name, self_contained)
  if (isTRUE(open)) {
    if (!is.function(viewer)) viewer <- utils::browseURL
    viewer(path)
  }
  invisible(path)
}

# ---- internal helpers -------------------------------------------------------

#' Folder holding the dashboard template and assets
#' @keywords internal
#' @noRd
d3_asset_dir <- function() {
  dir <- system.file("d3dashboard", package = "MolPad")
  if (!nzchar(dir)) stop("Could not find the d3dashboard assets. Is MolPad installed?")
  dir
}

#' Ordered asset paths (relative to the asset folder) from manifest.json
#' @keywords internal
#' @noRd
d3_assets <- function() {
  manifest <- jsonlite::fromJSON(file.path(d3_asset_dir(), "manifest.json"))
  list(css = as.character(manifest$css),
       lib = as.character(manifest$lib),
       js = as.character(manifest$js))
}

#' Replace `{{KEY}}` placeholders without regex interpretation
#' @keywords internal
#' @noRd
d3_fill_template <- function(template, values) {
  for (key in names(values)) {
    parts <- strsplit(template, paste0("{{", key, "}}"), fixed = TRUE)[[1]]
    # strsplit drops a trailing empty piece; keep it so a placeholder at the
    # very end of the template is still replaced.
    if (endsWith(template, paste0("{{", key, "}}"))) parts <- c(parts, "")
    template <- paste(parts, collapse = values[[key]])
  }
  template
}

d3_html_escape <- function(x) {
  x <- gsub("&", "&amp;", x, fixed = TRUE)
  x <- gsub("<", "&lt;", x, fixed = TRUE)
  x <- gsub(">", "&gt;", x, fixed = TRUE)
  x <- gsub("\"", "&quot;", x, fixed = TRUE)
  x
}

d3_read_asset <- function(rel) {
  paste(readLines(file.path(d3_asset_dir(), rel), warn = FALSE, encoding = "UTF-8"),
        collapse = "\n")
}

#' Write the dashboard HTML
#' @keywords internal
#' @noRd
d3_render_html <- function(payload, output_dir, file_name = "index.html",
                           self_contained = TRUE) {
  assets <- d3_assets()
  dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
  output_dir <- normalizePath(output_dir, winslash = "/", mustWork = TRUE)

  if (isTRUE(self_contained)) {
    styles <- vapply(assets$css, function(f) {
      paste0("<!-- molpad:", f, " -->\n<style>\n", d3_read_asset(f), "\n</style>")
    }, character(1))
    scripts <- vapply(c(assets$lib, assets$js), function(f) {
      paste0("<!-- molpad:", f, " -->\n<script>\n", d3_read_asset(f), "\n</script>")
    }, character(1))
  } else {
    for (sub in unique(dirname(c(assets$css, assets$lib, assets$js)))) {
      dir.create(file.path(output_dir, sub), recursive = TRUE, showWarnings = FALSE)
    }
    for (f in c(assets$css, assets$lib, assets$js)) {
      file.copy(file.path(d3_asset_dir(), f), file.path(output_dir, f), overwrite = TRUE)
    }
    styles <- paste0("<link rel=\"stylesheet\" href=\"", assets$css, "\">")
    scripts <- paste0("<script src=\"", c(assets$lib, assets$js), "\"></script>")
  }

  html <- d3_fill_template(
    d3_read_asset("index.html"),
    list(
      TITLE = d3_html_escape(payload$title),
      STYLES = paste(styles, collapse = "\n"),
      DATA_JSON = d3_payload_json(payload),
      SCRIPTS = paste(scripts, collapse = "\n")
    )
  )

  path <- file.path(output_dir, file_name)
  con <- file(path, open = "w", encoding = "UTF-8")
  on.exit(close(con))
  writeLines(enc2utf8(html), con, useBytes = TRUE)
  path
}

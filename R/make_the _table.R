#' Make table from brushed region
#'
#' @description
#' Generate the table of selected groups for the dashboard.
#'
#' @docType package
#' @name make_the_table
#' @param p ggplot output

#' @importFrom ggplot2 ggplot ggplot_build
#' @export
make_the_table <- function(p) {
  plot_df <- ggplot_build(p)
  plot_df$plot$data
}

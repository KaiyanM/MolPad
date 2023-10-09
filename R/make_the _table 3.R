#' make table
#'
#' Generate the table of selected groups for the dashboard.
#'
#' @docType data
#' @name make_the_table
#' @format .

#' @importFrom ggplot2 ggplot ggplot_build
#' @export
make_the_table <- function(p) {
  plot_df <- ggplot_build(p)
  plot_df$plot$data
}

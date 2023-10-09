#' process pathway
#'
#' Generate the cleaned version of the pathway for the dashboard.
#'
#' @docType data
#' @name ptw_process
#' @format A dataframe and a weblink column name
#' @examples data(stuff)
#' nao_ptw <- ptw_process(ptw, ko_term)
#' head(nao_ptw)
#' @importFrom dplyr bind_rows mutate filter group_by ungroup
#' @export
ptw_process <- function(ptw, ko_term) {
  nao_ptw <- na.omit(ptw)
  nao_ptw[, ko_term] <- paste0("https://www.kegg.jp/entry/", nao_ptw[, ko_term])
  nao_ptw[, ko_term] <- paste0("<a href='", nao_ptw[, ko_term], "' target='_blank'>", nao_ptw[, ko_term], "</a>")
  nao_ptw
}

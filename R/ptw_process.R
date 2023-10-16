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
ptw_process <- function(ptw, id_type) {
  nao_ptw <- na.omit(ptw)
  if(id_type == "KEGG"){
    nao_ptw[, "web_id"] <- paste0("https://www.kegg.jp/entry/", nao_ptw[, "web_id"])
  }else if(id_type == "GO"){
    nao_ptw[, "web_id"] <- paste0("https://www.ebi.ac.uk/QuickGO/term/", nao_ptw[, "web_id"])
  }
  nao_ptw[, "web_id"] <- paste0("<a href='", nao_ptw[, "web_id"], "' target='_blank'>", nao_ptw[, "web_id"], "</a>")
  nao_ptw
}


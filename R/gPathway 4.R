#' gPathway
#'
#' @description This function append the cluster information and the detailed feature ID to the pathway dataset.
#'
#' @docType package
#' @name gPathway
#'
#' @param pathway A data frame. The columns must include "ID", "taxonomic.scope", and "Pathway".
#' @param a The output of `pre_process()`
#' @param b The output of `gClusters()`
#'
#' @examples
#' data("FuncExample")
#' head(a)
#' head(b)
#' ptw <- gPathway(pathway, a, b)
#' head(ptw)
#'
#' @importFrom dplyr select
#' @export
gPathway <- function(pathway, a, b) {
  a |>
    mutate(cluster = paste0("Group_", b[[1]]$cluster)) |>
    select(c("ID", "cluster")) |>
    merge(pathway, by = "ID", all.x = TRUE)
}

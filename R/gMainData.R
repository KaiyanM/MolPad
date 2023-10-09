#' gMainData
#'
#' @description This function generate a main data-input for the dashboard.
#'
#' @docType package
#' @name gMainData
#'
#' @param data The output of `pre_process()`
#' @param clusters The output of `gClusters()`
#' @param pathway he output of `gPathway()`
#'
#' @importFrom tidyr pivot_longer 
#' @importFrom dplyr mutate left_join
#' @source scale()
#' @examples
#' data(FuncExample)
#' # inputs
#' head(a)
#' head(b)
#' head(ptw)
#' # generate dataset
#' dfgroup_long <- gMainData(a, b, ptw)
#' head(dfgroup_long)
#' @export
gMainData <- function(data, clusters, pathway) {
  clustersres <- clusters[[1]]
  maindata <- data |>
    mutate(cluster = paste0("Group_", clustersres$cluster)) |>
    pivot_longer(
      c(-ID, -cluster, -type),
      names_to = "day",
      values_to = "value"
    ) |>
    mutate(day = factor(day, levels = colnames(data)[c(-1, -ncol(data))])) |>
    left_join(select(pathway, ID, taxonomic.scope), by = "ID")

  maindata$taxonomic.scope[is.na(maindata$taxonomic.scope)] <- "No Label"
  maindata
}

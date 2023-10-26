#' scale_by_row
#'
#' This function scales the values in the rows for all non-ID columns.
#'
#' @docType package
#' @name scale_by_row__
#' @format A data frame in which the first column is ID and the rest are
#' observations for different time points. Note that the first column should be ID
#' and thus will not be scaled, and the rest of the columns require dbl format.
#' @source scale()
#' @examples data(fungal)
#' scale_by_row__(fungal[[3]])
#' @export
scale_by_row__ <- function(data){
  to_scale <- data[,(unlist(lapply(data, is.numeric)))&(names(data) %in% c("ID","id","Id")==FALSE)]
  scaled <- as.data.frame(t(apply(to_scale, 1, scale)))
  data[,(unlist(lapply(data, is.numeric)))&(names(data) %in% c("ID","id","Id")==FALSE)] <- scaled
  data
}

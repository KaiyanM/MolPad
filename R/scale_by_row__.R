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
  d <- as.data.frame(t(apply(data[,-1], 1, scale)))
  d <- cbind(data[,1], d)
  colnames(d) <- colnames(data)
  d
}

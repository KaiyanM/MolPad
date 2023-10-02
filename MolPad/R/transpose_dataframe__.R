#' transpose dataframe
#'
#' This function transpose a given data frame, converting the first column to new column names
#'
#' @docType package
#' @name transpose_dataframe__
#' @format A data frame in which the first column is ID and the rest are observations for different time points.
#' @examples data(fungal)
#' transpose_dataframe__(fungal[[3]])
#' @export
transpose_dataframe__ <- function(data){
  data <- data.frame(t(data))
  names(data) <- data[1,]
  data <- data[-1,]
  data <- as.data.frame(sapply(data,as.numeric))
  return(data)
}
NULL

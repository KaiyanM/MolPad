#' Scale by row
#' 
#' @description
#' Scales the values for each sample, where each row is independently processed.
#'
#' @docType package
#' @name scale_by_row__
#' 
#' @details
#' The input is expected to be a data frame with the first column as the ID and the following columns containing observations at different time points. The ID column remains unaltered, and the other columns should be in double (dbl) format and will be scaled.
#' 
#' @examples data(test_data)
#' scale_by_row__(test_data[1:5,1:10])
#' 
#' @export
scale_by_row__ <- function(data){
  to_scale <- data[,(unlist(lapply(data, is.numeric)))&(names(data) %in% c("ID","id","Id")==FALSE)]
  scaled <- as.data.frame(t(apply(to_scale, 1, scale)))
  data[,(unlist(lapply(data, is.numeric)))&(names(data) %in% c("ID","id","Id")==FALSE)] <- scaled
  data
}

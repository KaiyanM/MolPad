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
#' @param data A data frame with an ID column and numeric time columns.
#' @param groups Optional named list of column names. When given, each row is scaled separately within every group of columns (for example one group per subject) instead of across all numeric columns.
#'
#' @examples data(test_data)
#' scale_by_row__(test_data[1:5,1:10])
#' scale_by_row__(test_data[1:5,1:11], groups = list(a = paste0("T", 1:5), b = paste0("T", 6:10)))
#' 
#' @export
scale_by_row__ <- function(data, groups = NULL){
  if (!is.null(groups)) {
    for (g in groups) {
      m <- as.matrix(as.data.frame(data)[, g, drop = FALSE])
      storage.mode(m) <- "double"
      data[g] <- as.data.frame((m - rowMeans(m)) / apply(m, 1, stats::sd))
    }
    return(data)
  }
  to_scale <- data[,(unlist(lapply(data, is.numeric)))&(names(data) %in% c("ID","id","Id")==FALSE)]
  scaled <- as.data.frame(t(apply(to_scale, 1, scale)))
  data[,(unlist(lapply(data, is.numeric)))&(names(data) %in% c("ID","id","Id")==FALSE)] <- scaled
  data
}

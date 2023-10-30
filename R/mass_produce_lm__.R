#' Produce linear model for each column
#'
#' @description  
#' This is an internal function designed to automatically generate a list of linear functions for a dataset. Each column is considered a response variable against all other columns. The resulting functions can be utilized as inputs for random forest regression.
#' 
#' @docType package
#' @name mass_produce_lm__
#' 
#' @param data A dataframe.
#' 
#' @export
mass_produce_lm__ <- function(data) {
  lfml <- list()
  for (i in 1:ncol(data)) {
    right <- paste(colnames(data)[-i], collapse = "+")
    fml <- formula(paste0(colnames(data)[i], "~", right))
    lfml <- append(lfml, fml)
  }
  lfml
}

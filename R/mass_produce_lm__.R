#' Mass produce linear model
#'
#' @description  
#' Take each column as dependent vairable at a time, and produce n linear models for n columns in a dataset.
#' 
#' @details
#' This is an internal function designed to automatically generate a list of functions for regression. Each column is considered a response variable against all other columns. The resulting functions can be utilized as inputs for random forest regression in `gNetwork()`.
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

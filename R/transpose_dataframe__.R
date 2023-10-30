#' Transpose dataframe
#' 
#' @description
#' This function transposes a provided data frame, using the values from the first column as new column names.
#'
#' @docType package
#' @name transpose_dataframe__
#' 
#' @details
#' The expected input is a data frame where the first column serves as `Time`, and the subsequent columns contain observations for various features.
#' 
#' @examples 
#' a <- data.frame("Day"=c("Day1","Day2","Day3"),"feature_1" =c(1,2,3),"feature_2" =c(0,4,1),"feature_3" =c(1,1,0))
#' a
#' transpose_dataframe__(a)
#' 
#' @export
transpose_dataframe__ <- function(data){
  data <- data.frame(t(data))
  names(data) <- data[1,]
  data <- data[-1,]
  data <- as.data.frame(sapply(data,as.numeric))
  return(data)
}
NULL

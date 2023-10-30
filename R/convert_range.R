#' Convert range
#'
#' @description An internal function for range conversion. For each element in x, it returns the distance to the minimal values and divided by the range.
#' @param x A vector of numbers.

#' @docType package
#' @name convert_range
#' 

#' @export
convert_range <- function(x) {
  (x - min(x)) / (max(x) - min(x))
}

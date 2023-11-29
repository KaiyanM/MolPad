#' Convert range
#'
#' @description An internal function for range conversion. For each element in x, it returns the distance to the minimal values and divided by the range.
#' @param x A vector of numbers.
#' @return A vector calculated by (x - min(x)) / (max(x) - min(x))
#' @docType package
#' @name convert_range
#' 
#' @examples
#' convert_range(5:10)
#' 
#' @export
convert_range <- function(x) {
  (x - min(x)) / (max(x) - min(x))
}

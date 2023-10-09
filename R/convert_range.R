#' @export
convert_range <- function(x) {
  (x - min(x)) / (max(x) - min(x))
}

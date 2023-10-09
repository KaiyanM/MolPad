#' @export
extend.color__ <- function(n, colors, extendby = 1, alpha = 1, ...) {
  k <- length(colors)
  if (n <= k) {
    return(colors)
  } else {
    if (extendby == 1) {
      return(c(colors, rainbow(n - k, alpha)))
    }
    if (extendby == 2) {
      return(c(colors, heat.colors(n - k), alpha))
    }
    if (extendby == 3) {
      return(c(colors, terrain.colors(n - k), alpha))
    }
    if (extendby == 4) {
      return(c(colors, topo.colors(n - k), alpha))
    }
    if (extendby == 5) {
      return(c(colors, colors()[seq(from = 1, by = 5, length.out = n - k)]))
    }
  }
}

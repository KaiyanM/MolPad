#' Extend color palettes
#'
#' @description An internal function designed to pair vectors with color palettes and automatically generate colors for longer vectors that cannot find a match.
#' @param n A number. The length of feature vector that you want to match with the colors.
#' @param colors A vector of colors (finite).
#' @param extendby A number to select from 1, 2, 3, 4 or 5, representing distinct auto-fill schemes.
#' @param alpha A number to select from range [0,1].

#' @docType package
#' @name extend.color__

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

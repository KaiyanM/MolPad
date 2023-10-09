#' @export
match.color__ <- function(valist, mycolors, extendby = 5) {
  if (length(valist) <= length(mycolors)) {
    mycolors <- mycolors[seq_along(valist)]
  } else {
    mycolors <- extend.color__(length(valist), mycolors, extendby = extendby)
  }
  names(mycolors) <- valist
  mycolors
}

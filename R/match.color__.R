#' Match color
#' 
#' @description
#' Match any vector with a finite list of colors. 
#'
#' @docType package
#' @name match.color__
#' 
#' @param valist A vector that you want to specify the colors for each element. 
#' @param mycolors A vector of colors.
#' @param extendby A number to select from 1, 2, 3, 4, or 5, representing distinct auto-fill schemes.

#' 
#' @examples 
#' my_vector <- paste0("N_",1:10)
#' match.color__(my_vector,c("red","yellow","blue"))
#' 
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

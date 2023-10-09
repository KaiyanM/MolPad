#' mass_produce_lm__
#'
#' @name mass_produce_lm__
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

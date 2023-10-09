#' @export
#' @import shiny
#' @import shinydashboard
#' @importFrom cli cli_abort
runExample <- function() {
  appDir <- system.file("shiny-examples", "myapp", package = "pkg")
  if (appDir == "") {
    cli_abort("Could not find example directory. Try re-installing package.")
  }

  runApp(appDir, display.mode = "normal")
}

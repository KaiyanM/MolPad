## how to document datasets: you need to specify @docType and @name; do not
## forget NULL in the end

#' loads PNNL dataframes
#' 
#' 
#' @format A data frame with 234 rows and 11 variables:
#' \describe{
#'   \item{manufacturer}{manufacturer name}
#'   \item{model}{model name}
#'   \item{displ}{engine displacement, in litres}
#'   \item{year}{year of manufacture}
#'   \item{cyl}{number of cylinders}
#'   \item{trans}{type of transmission}
#'   \item{drv}{the type of drive train, where f = front-wheel drive, r = rear wheel drive, 4 = 4wd}
#'   \item{cty}{city miles per gallon}
#'   \item{hwy}{highway miles per gallon}
#'   \item{fl}{fuel type}
#'   \item{class}{"type" of car}
#' }
#'
#' This function loads three PNNL dataframes: dfgroup_long, ptw and res.
#' @docType data
#' @name cheese
#' @format dataframe
#' @source cheese data
#' @examples data(cheese)
#' head(c12)
#' head(f12)
#' head(t12)
NULL

#' Cheese data
#' 
#' @description
#' In the context of cheese production, the regular application of a brine solution is a maturation technique that promotes uniformity in the microbial populations on the cheese's surface and facilitates interactions among these microorganisms. This investigation involved the analysis of a longitudinal dataset encompassing three washed-rind cheese communities sampled during the ripening process.
#' 
#' @details
#' The study uncovered a remarkably consistent microbial progression within each cheese. In the bacterial community, Firmicutes dominate at the outset, with Proteobacteria swiftly assuming dominance by the end of the ripening period. Additionally, both Cheese A and Cheese C consistently demonstrate the establishment of Actinobacteria and Bacteroidetes, each in its own distinct manner. To corroborate these findings using the MolPad dashboard, we conducted an analysis of two cheeses (A and C) from all three production batches, spanning weeks 2 to 13.
#' 
#' @format two datasets: `cheese` and `annotations`
#' 
#' @section cheese data: 
#' A data frame with 29423 rows and 11 variables:
#' \describe{
#'   \item{ID}{sample ID}
#'   \item{A1~A5}{Time series data measured for cheese 1.}
#'   \item{B1~B5}{Time series data measured for cheese 2.}
#' }
#' 
#' @section annotation data: 
#' A data frame with 29423 rows and 10 variables:
#' \describe{
#'   \item{ID}{sample ID}
#'   \item{GO_ID}{GO IDs, represents a link between a gene product type and a molecular function}
#'   \item{KEGG_ID}{KEGG IDs, linking genomic information with higher order functional information.}
#'   \item{Other_ID}{other IDs in online databases}
#'   \item{kingdom}{the category of the feature}
#'   \item{phylum}{the category of the feature}
#'   \item{class}{the category of the feature}
#'   \item{order}{the category of the feature}
#'   \item{family}{the category of the feature}
#'   \item{genus}{the category of the feature}
#' }
#'
#' @docType data
#' @name cheese
#' 
#' @source Reference: doi:10.1128/msystems.00701-22
#' @examples data(cheese)
#' head(annotations)
#' head(cheese)
NULL

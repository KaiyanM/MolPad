#' Fungal garden data
#' 
#' @description
#' Fungal gardens in fungus-growing ants function as an external digestive system, where mutualistic fungi of the genus Leucoagaricus convert plant substrate into energy. In this study, a naturally evolved fungal garden consortium underwent gradual infection by a pathogenic fungus, Escovopsis, creating a dynamic system for investigation. The researchers analyzed the bacterial taxa in this system to track community shifts and spatial activity mapping.
#' @details
#' As microorganisms can provide defense by competitively excluding pathogenic microbes, a central question was to uncover changes in population compositions and metabolic potentials within this intricate microbial consortium in response to perturbation. To grasp this matter, we can employ the MolPad dashboard to examine a particular pathway and unveil its pattern across various subtypes.
#' 
#' @format two datasets:  `fungal_garden` and `pathway`
#' 
#' @section Fungal garden data: 
#' A list that contains 3 dataframes:
#' \describe{
#'   \item{ID}{sample ID}
#'   \item{D0_01~D10_11}{measured values in the corresponding days}
#' }
#' 
#' @section Pathway: 
#' A data frame with 126725 rows and 4 variables:
#' \describe{
#'   \item{ID}{sample ID}
#'   \item{taxonomic.scope}{the category of the feature}
#'   \item{ko_term}{KEGG IDs, linking genomic information with higher order functional information.}
#'   \item{Pathway}{KEGG pathways, representation focuses on the network of gene products, mostly proteins but including functional RNAs.}
#' }

#' @docType data
#' @name fungal_garden

#' @source Generated from PNNL
#' @examples data(fungal_garden)
#' head(fungal_dlist[[1]],3)
#' head(fungal_dlist[[2]],3)
#' head(fungal_dlist[[3]],3)
#' head(pathway,3)
NULL

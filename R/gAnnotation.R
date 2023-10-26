#' generate processed annotation
#'
#' @description `gAnnotation()` returns the 
#'
#' @details This function could 
#' 
#' @docType package
#' @name gAnnotation
#'
#' @param data A dataframe.
#' @param first_order The name of one column of categorical variable in `data`.
#' @param second_order The name of another column of categorical variable in `data`.
#'
#' @examples data(test_data)
#' test_annotations_processed <- gAnnotation(test_annotations,system,class)
#' head(test_annotations_processed)
#' 
#' @details
#' Guidelines for Selecting Annotations:
#' *The first-order annotation is recommended to be functional, such as a pathway or functional system. This parameter will primarily serve the purpose of filtering out one network at a time when displaying the dashboard. 
#' *The second-order annotation is utilized to illustrate the composition of a first-order annotation using a bar plot. Therefore, it is better to set it as taxon, class label, etc.
#' 
#' @importFrom tidyr replace_na
#' @importFrom dplyr rename mutate_at
#' @export
gAnnotation <- function(data,first_order,second_order) {
  strings <- c(as.character(substitute(first_order)), 
               as.character(substitute(second_order)))
  data %>%
    dplyr::rename("Pathway" = strings[1],
           "taxonomic.scope" = strings[2]) %>%
    dplyr::mutate_at(c("Pathway","taxonomic.scope"), ~replace_na(.,"Unknown"))
}

#' Generate processed annotation
#'
#' @description `gAnnotation()` provides the standard input format for the dashboard, allowing users to select two columns as the primary factors they wish to visualize and describe in the data.

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
#' * The first-order annotation is recommended to be functional, such as a pathway or functional system. This parameter will primarily serve the purpose of filtering out one network at a time when displaying the dashboard.
#' * The second-order annotation is utilized to illustrate the composition of a first-order annotation using a bar plot. Therefore, it is better to set it as taxon, class label, etc.
#' 
#' @importFrom tidyr replace_na
#' @importFrom dplyr rename mutate_at 
#' @importFrom rlang enquo
#' @export
gAnnotation <- function(data,first_order,second_order) {
  l <- c(as.character(substitute(first_order)), as.character(substitute(second_order)))
  data %>%
    dplyr::rename("Pathway" = !!rlang::enquo(first_order),
           "taxonomic.scope" = !!rlang::enquo(second_order)) %>%
    dplyr::mutate_at(c("Pathway","taxonomic.scope"), ~replace_na(.,"Unknown"))
}

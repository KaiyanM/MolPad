#' Generate processed annotation
#'
#' @description `gAnnotation()` provides the standard input format for the dashboard, allowing users to select two columns as the primary factors they wish to visualize and describe in the data.

#' @docType package
#' @name gAnnotation
#'
#' @param data A data.frame containing annotations that should be used for describing the features we measured at each time point. It is also required to include `ID` and at least two categorical variables.
#' @param first_order A string. The name of one column of categorical variable in `data`. 
#' @param second_order A string. The name of another column of categorical variable in `data`.
#' @param study Optional. The output of [gStudy()]: when `first_order` or `second_order` is left out, the `level1` and `level2` columns of the study are used.
#'
#' @examples data(test_data)
#' test_annotations_processed <- gAnnotation(test_annotations,system,class)
#' head(test_annotations_processed)
#' 
#' @details
#' Guidelines for Selecting Annotations:
#' * The first-order annotation is recommended to be functional, such as a pathway or functional system. This parameter will primarily serve the purpose of filtering out one network at a time when displaying the dashboard.
#' * The second-order annotation is utilized to illustrate the composition of a first-order annotation using a bar plot. Therefore, it is better to set it as taxon, class label, etc.
#' * The two columns are renamed to `Pathway` and `taxonomic.scope`. Their original names are kept in the attribute `molpad_levels`, which `gDashboard_d3()` writes into the page.
#' 
#' @importFrom tidyr replace_na
#' @importFrom dplyr rename mutate_at 
#' @importFrom rlang enquo
#' @export
gAnnotation <- function(data,first_order,second_order,study=NULL) {
  study <- as_study__(study)
  if (missing(first_order) || missing(second_order)) {
    # the level columns come from the study
    l <- c(if (missing(first_order)) study$level1$column else as.character(substitute(first_order)),
           if (missing(second_order)) study$level2$column else as.character(substitute(second_order)))
    if (length(l) != 2) {
      stop("Give `first_order` and `second_order`, or a `study` with `level1` and `level2`.")
    }
    bad <- setdiff(l, colnames(data))
    if (length(bad)) stop("The annotation has no column named: ", paste(bad, collapse = ", "), ".")
    first_order <- as.name(l[1])
    second_order <- as.name(l[2])
  } else {
    l <- c(as.character(substitute(first_order)), as.character(substitute(second_order)))
  }
  out <- data %>%
    dplyr::rename("Pathway" = !!rlang::enquo(first_order),
           "taxonomic.scope" = !!rlang::enquo(second_order)) %>%
    dplyr::mutate_at(c("Pathway","taxonomic.scope"), ~replace_na(.,"Unknown"))
  # the columns are renamed for the dashboard; keep what they were called, so that
  # gDashboard_d3() can write down what level 1 and level 2 are in this dataset
  if (length(l) == 2) attr(out, "molpad_levels") <- list(level1 = l[1], level2 = l[2])
  if (!is.null(study)) attr(out, "molpad_study") <- study
  out
}

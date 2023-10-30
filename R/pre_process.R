#' Pre-processing datasets
#'
#' @description The `pre_process()` function aids in processing data inputs and automatically establishes a standardized format for future use. It allows for two types of data input: a list of datasets from different sources or a long dataset containing a specified column `type`. It's important to note that for each dataset, the initial column is designated for `ID`s, while the subsequent columns are expected to contain values measured on Time1, Time2, and so forth.
#' @docType package
#' @name pre_process
#'
#' @param data A list of datasets or a long dataset.
#' @param typenameList A vector of dataset names. This parameter is only applicable when the input format is a list.
#' @param replaceNa Logical; if TRUE (default), replace NA with 0.
#' @param scale Logical; if TRUE (default), scale the datasets by row. See also \link[MolPad]{scale_by_row__}
#' @param autoColName A string; if it's not NULL (default), automatically set uniform column names for all the datasets.This parameter is only applicable when the input format is a list.
#'
#' @details
#' We consider two distinct scenarios for this application:
#' *In one scenario, individuals collect several datasets from various aspects and instruments for the same objects. For example, they might be separately detecting lipids, metabolites, and peptides from a specific soil sample.
#' *In the other scenario, all the data is of uniform quality, but it can be categorized into larger groups that exhibit significant differences.
#' In both of these cases, the pre_process() function serves as a valuable and versatile tool. Yet, this function is optional when generating the dashboard. Users can perform their own processing as long as the format matches the required output. However, they should be mindful that the number of samples (timepoints) must be greater than 5 to avoid potential errors in the subsequent prediction section.
#' 
#' @returns A long dataset with columns for ID, Time1, Time2, ..., and type.
#' 
#' @examples
#' data(test_data)
#' head(test_data, 10)
#' a <- pre_process(test_data)
#' head(a, 10)
#' 
#' @importFrom dplyr bind_rows
#' @export
pre_process <- function(data, typenameList = NULL, replaceNA = TRUE,
                        scale = TRUE, autoColName = "Day_") {
  if(is.data.frame(data)==FALSE){
    print("Reformat a list of datasets:")
    # set default type names
    if (is.null(typenameList)==FALSE) {
      typenameList <- paste0("Dataset_", seq_along(data))
    }
    for (i in seq_along(data)) {
      # set uniform column names
      if (is.null(autoColName)) {
        colnames(data[[i]]) <- c("ID", paste0(autoColName, 1:(ncol(data[[i]]) - 1)))
      }
      # replace NA with 0
      if (replaceNA) {
        data[[i]][is.na(data[[i]])] <- 0
      }
      # scale by feature (by row)
      if (scale) {
        data[[i]] <- scale_by_row__(data[[i]])
      }
      # add type name to corresponding data
      data[[i]]$type <- rep(typenameList[i], nrow(data[[i]]))
    }
    
    data <- data |>
      bind_rows() |>
      mutate(ID = as.factor(ID))
    

  }
  
  else{
    data$type[is.na(data$type)] <- "Other"
    if (replaceNA) {
      data[is.na(data)] <- 0
    }
    if(scale){
      data <- scale_by_row__(data) |> na.omit()
    }
  }
  
  return(data)
}

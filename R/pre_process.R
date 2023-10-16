#' pre_process
#'
#' @description This function preprocess the data-inputs and automatically sets uniform format for future use.
#'
#' @docType package
#' @name pre_process
#'
#' @param data A list of datasets. Note that for each dataset, the first columns should be ID and the rest columns are Time1, Time2, ...
#' @param typenameList A vector of dataset names.
#' @param replaceNa Logical; if TRUE (default), replace NA with 0.
#' @param scale Logical; if TRUE (default), scale the datasets by row. See also \link[pkg]{scale_by_row__}
#' @param autoColName A string; if it's not NULL (default), automatically set uniform column names for all the datasets.
#'
#' @examples
#' data(samples)
#' a <- pre_process(samples)
#' head(a, 10)
#' @importFrom dplyr bind_rows
#' @export
pre_process <- function(data, typenameList = NULL, replaceNA = TRUE,
                        scale = TRUE, autoColName = "Day_") {
  if(is.data.frame(data)==FALSE){
    print("Reformat a list of datasets:")
    # set default type names
    if (is.null(typenameList)) {
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

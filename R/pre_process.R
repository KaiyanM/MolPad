#' pre_process
#'
#' @description This function preprocess the data-inputs and automatically sets uniform format for future use.
#'
#' @docType package
#' @name pre_process
#'
#' @param dataList A list of datasets. Note that for each dataset, the first columns should be ID and the rest columns are Time1, Time2, ...
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
pre_process <- function(dataList, typenameList = NULL, replaceNA = TRUE,
                        scale = TRUE, autoColName = "Day_") {
  if(class(dataList) == "list"){
    # set default type names
    if (is.null(typenameList)) {
      typenameList <- paste0("Dataset_", seq_along(dataList))
    }
    for (i in seq_along(dataList)) {
      # set uniform column names
      if (is.null(autoColName)) {
        colnames(dataList[[i]]) <- c("ID", paste0(autoColName, 1:(ncol(dataList[[i]]) - 1)))
      }
      # replace NA with 0
      if (replaceNA) {
        dataList[[i]][is.na(dataList[[i]])] <- 0
      }
      # scale by feature (by row)
      if (scale) {
        dataList[[i]] <- scale_by_row__(dataList[[i]])
      }
      # add type name to corresponding data
      dataList[[i]]$type <- rep(typenameList[i], nrow(dataList[[i]]))
    }
    
    dataList |>
      bind_rows() |>
      mutate(ID = as.factor(ID))
  }
  
  if (class(dataList) == "data.frame") {
    dataList$type[is.na(dataList$type)] <- "Other"
    if (replaceNA) {
      dataList[is.na(dataList)] <- 0
    }
    if(scale){
      dataList <- scale_by_row__(dataList) |> na.omit()
    }
    dataList
  }
  else{
    print("'dataList' can only be a list of datasets or a single dataset.")
  }
}

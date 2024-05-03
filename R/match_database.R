#' Match database
#'
#' @description
#' matches the selected columns with online database names.
#' 
#' @details
#' `match_database()` is an internal function that matches the selected columns in the dataset with corresponding databases. Currently MolPad support two types of annotation database: GO and KEGG. If you want to custom the URL for other platform, you could download and modify on `paste_URL()` function.
#'
#' @docType package
#' @name match_database
#' 
#' @examples data(test_data)
#' head(test_annotations_processed)
#' head(match_database(test_annotations_processed,id_colname = c("GO_ID","KEGG_ID"),id_type = c("GO","KEGG")))
#' 
#' @export
match_database <- function(data,id_colname,id_type){
  if(length(id_colname)!=length(id_type)){
    print("id_colname and id_type must have the same length.")
  }else{
    for (i in 1:length(id_colname)) {
      data[[id_colname[i]]] <-  paste_URL(data[[id_colname[i]]],id_type[i])
    }
    data
  }
}

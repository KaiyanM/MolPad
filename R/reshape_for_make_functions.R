#' Reshape for 'make' functions
#'
#' @description This internal function produces three primary datasets for the dashboard intended for the "make" functions.
#'
#' @docType package
#' @name reshape_for_make_functions
#'
#' @param data The output of `pre_process()`
#' @param cluster The output of `gClusters()`
#' @param annotation The output of `gPathway()`
#' @param id_colname The columns that contain database IDs.
#' @param id_type The corresponding database names for the above columns.
#'
#' @examples data(test_data)
#' l <- reshape_for_make_functions(test_data_processed, test_cluster, test_annotations_processed, id_colname = c("GO_ID","KEGG_ID"),id_type = c("GO","KEGG"))
#' head(l[[1]])
#' head(l[[2]])
#' head(l[[3]])
#' 
#'
#' @importFrom tidyr pivot_longer 
#' @importFrom dplyr mutate left_join select
#' @export
reshape_for_make_functions <- function(data, cluster, annotation, id_colname, id_type) {
  
  data_cluster <- data |>
    mutate(cluster = paste0("Group_", cluster[[1]]$cluster)) 
  
  #ptw: id cluster columns in annotation
  output_graphptw <- data_cluster |>
    select(c("ID", "cluster")) |>
    merge(annotation, by = "ID", all.x = TRUE)
  
  #dfgroup_long: id type cluster day value taxonomic.scope
  output_maindata <- data_cluster |>
    pivot_longer(
      c(-ID, -cluster, -type),
      names_to = "day",
      values_to = "value"
    ) |>
    mutate(day = factor(day, levels = colnames(data)[c(-1, -ncol(data))])) |>
    left_join(select(annotation, ID, taxonomic.scope), by = "ID")
  
  if(is.null(id_colname)|is.null(id_type)){
    output_tableview <- output_graphptw
  }else{
    output_tableview <- output_graphptw |>
      match_database(id_colname,id_type)
  }
  
  #output_tableview$web_id <- paste_URL(output_tableview$web_id,id_type)
  
  list(output_graphptw = output_graphptw,
       output_maindata = output_maindata,
       output_tableview = output_tableview)

}

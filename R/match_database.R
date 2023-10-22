#' match database
#'
#' Generate the cleaned version of the pathway for the dashboard.
#'
#' @docType package
#' @name match_database
#' @format A dataframe and a weblink column name
#' @examples data(stuff)
#' nao_ptw <- ptw_process(ptw, ko_term)
#' head(nao_ptw)
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

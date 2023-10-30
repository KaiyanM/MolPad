#' Paste URL
#' 
#' @description
#' Retrieve database IDs and associate them with their respective URLs.
#' 
#' @docType package
#' @name paste_URL
#' 
#' @examples data(test_data)
#' paste_URL(test_annotations$GO_ID[1:4], id_type = "GO")
#' 
#' @importFrom stringr str_extract_all
#' @export
paste_URL <- function(x,id_type){
  output_list <- c()
  if(id_type=="KEGG"){
    extract_multiple_id <- str_extract_all(x,"K\\d{5}")
    link <- "https://www.kegg.jp/entry/"
  }else if(id_type=="GO"){
    extract_multiple_id <- str_extract_all(x,"GO:\\d{7}")
    link <- "https://www.ebi.ac.uk/QuickGO/term/"
  }else{
    print("ID must be one of the following: KEGG, GO")
  }
  
  for (i in 1:length(x)) {
    if(length(extract_multiple_id[[i]]) != 0){
      for (j in 1:length(extract_multiple_id[[i]])) {
        extract_multiple_id[[i]][j] <- paste0("<a href='",link,extract_multiple_id[[i]][j],"' target='_blank'>",extract_multiple_id[[i]][j],"</a>")
      }
      output_list[i] <- paste(extract_multiple_id[[i]], collapse = '<br/>')
    }else{
      output_list[i] <- NA
    }
  }
  output_list
}


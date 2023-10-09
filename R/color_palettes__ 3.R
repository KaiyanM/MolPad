#' @export
color_palettes__ <- function(name){
  if(name == "graytone"){
    return(c("#c3c5c7","#30beba","#998a73","#807566","#a5b1c9","#5d5232","#9a2b41","#d6b7a2","#882db4","#b47a53"))
  }
  if(name == "darkwarm"){
    return(c("#251305","#C70A80","#FBCB0A","#ff1122","#7D7463","#CECE5A","#FF9B9B","#A459D1","#00235B","#7E1717"))
  }
  return("No such palette. Please check the name and try again.")
}

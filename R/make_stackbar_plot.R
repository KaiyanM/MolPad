#' Make stackbar plot
#' 
#' @description
#' Generate the stackbar plot for the dashboard.
#'
#' @docType data
#' @name make_stackbar_plot

#' @source ggplot2::geom_bar
#' 
#' @examples data(test_data)
#' make_stackbar_plot(test_maindata, "Group_5", c("hormonal proteins","structural proteins","enzymes","storage proteins","antibodies","transport proteins"))
#' 

#' @import dplyr
#' @import ggplot2
#' @importFrom grid unit
#' @export
make_stackbar_plot <- function(dfgroup_long,selected_groups, selected_taxa){
  matchcolor <- unique(dfgroup_long$taxonomic.scope)

  dfgroup_long_filter_cluster <- dfgroup_long  %>%
    filter(cluster %in% selected_groups) %>%
    count(cluster, taxonomic.scope) %>%
    filter(taxonomic.scope %in% selected_taxa)

  assigncol <- match.color__(unique(dfgroup_long$taxonomic.scope),color_palettes__("graytone"))

  ggplot(dfgroup_long_filter_cluster, aes(x = cluster,y=n, fill = taxonomic.scope)) +
    geom_bar(stat = "identity") +
    coord_flip()+
    theme(legend.position="top",
          legend.title = element_text(size=11),
          legend.text = element_text(size=11),
          legend.key.size = unit(0.5, "cm"))+
    scale_fill_manual(values = assigncol)

}

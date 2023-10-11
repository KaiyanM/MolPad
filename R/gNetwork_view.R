#' gNetwork_view
#'
#' @description Generate a feature importance plot for the random forest result.
#'
#' @docType package
#'
#' @param data The output of `gNetwork()`
#' @source scale()
#' @examples
#' data(FuncExample)
#' gNetwork_view(networkres)
#' @name gNetwork_view
#' @importFrom ggplot2 geom_segment theme_light coord_flip ylab xlab ggtitle theme element_blank facet_wrap
#' @export
gNetwork_view <- function(data) {
  options(repr.plot.width = 9, repr.plot.height = 15)
  data %>%
    ggplot(aes(var_names, weight)) +
    geom_segment(aes(xend = var_names, y = 0, yend = weight), color = "skyblue") +
    geom_point(aes(size = IncNodePurity), color = "blue", alpha = 0.6) +
    theme_light() +
    coord_flip() +
    ylab("Per cent increase in MSE") +
    xlab("Cluster centers") +
    ggtitle(
      paste0("Top ", "n ", "Feature Importance"), 
      subtitle = "for predicting each group"
    ) +
    theme(
      legend.position = "bottom",
      panel.grid.major.y = element_blank(),
      panel.border = element_blank(),
      axis.ticks.y = element_blank()
    ) +
    facet_wrap(~from)
}

#' View the feature importance plot
#'
#' @description `gNetwork_view()` Generate a feature importance plot for the random forest result. This plot visually highlights the importance of individual cluster within a dataset, helping to identify key factors in predictive modeling.
#'
#' @docType package
#'
#' @param data A dataframe; The output of `gNetwork()`, including 4 variables: `weight`, `IncNodePurity`, `var_names` and `from`. The weight is the edge value, the IncNodePurity(%IncMSE) is the measure of predictions as a result of `var_names` being permuted. `from` is the dependent variable in each round of random forest.

#' @examples
#' data(test_data)
#' gNetwork_view(test_network)
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

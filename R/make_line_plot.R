#' Make line plot
#'
#' @description
#' Generate the line and ribbon plot for the dashboard.
#'
#' @docType data
#' @name make_line_plot

#' @details
#' this function makes a ribbon plot for every brush action in the Shiny to show the min, max, and mean value of each clustered pattern group across time. The ribbon plot is grouped and colored by the `type` variable in input datasets.
#' See also `ggplot2::geom_ribbon`.
#' 
#' @examples data(test_data)
#' make_line_plot(test_maindata, "Group_5", c("hormonal proteins","structural proteins","enzymes","storage proteins","antibodies","transport proteins"))
#' 

#' @importFrom grid unit
#' @importFrom dplyr filter summarise_at n_distinct
#' @importFrom ggplot2 scale_fill_manual scale_color_manual element_text
#' @export
make_line_plot <- function(dfgroup_long, selected_groups, selected_taxa) {
  colorinput <- extend.color__(
    n_distinct(dfgroup_long$type),
    color_palettes__("darkwarm")
  )

  dfgroup_long |>
    filter(
      (type %in% c("Metabolite", "Lipid") | 
      (taxonomic.scope %in% selected_taxa)),
      cluster %in% selected_groups
    ) |>
    group_by(day, type, cluster) |>
    summarise_at(
      "value",
      list(minvalue = min, meanvalue = mean, maxvalue = max)
    ) |>
    ggplot(aes(day, meanvalue)) +
    geom_ribbon(
      aes(ymin = minvalue, ymax = maxvalue, fill = type, group = type),
      alpha = 0.2
    ) +
    geom_line(aes(color = type, group = type), alpha = 0.8) +
    facet_wrap(cluster ~ ., scales = "free") +
    scale_fill_manual(values = colorinput) +
    scale_colour_manual(values = colorinput) +
    ggtitle("Pattern of Selected Groups") +
    xlab("Time") +
    ylab("Value") +
    theme(axis.text.x = element_text(angle = 90, vjust = 0.5, hjust = 1))
}

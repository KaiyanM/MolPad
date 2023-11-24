#' Make graph plot
#' 
#' @description
#' Generate the graph for the dashboard.
#'
#' @docType package
#' @name make_the_graph

#' @source ggraph::ggraph
#' 
#' @examples data(test_data)
#' make_the_graph(test_graphptw, test_network, 0.03, "Muscular System","kk")
#' 
#' @importFrom igraph graph_from_data_frame
#' @importFrom ggraph ggraph geom_edge_link geom_node_label scale_edge_alpha
#' @importFrom ggplot2 scale_fill_gradient ggtitle aes scale_fill_gradient
#' @export
make_the_graph <- function(ptw, network_output, min_weight, s_ptw, graph_layout) {
  ptw <- ptw[!is.na(ptw$Pathway), ]
  data <- data.frame(
    "from" = network_output$from,
    "to" = network_output$var_names,
    "weight" = network_output$weight
  )
  ncluster <- n_distinct(network_output$from)

  #-----------------------------------------------

  count_group <- ptw[ptw$Pathway == s_ptw, ] |> count(cluster, sort = TRUE)

  if (nrow(count_group) < ncluster) {
    missing_group <- unique(data$from)[!(unique(data$from) %in% count_group$cluster)]
    count_group <- rbind(
      count_group,
      data.frame(cluster = missing_group, n = rep(0, length(missing_group)))
    )
  }
  

  g <- filter(data, weight > min_weight) |>
    graph_from_data_frame(directed = FALSE, vertices = count_group)

  g |>
    ggraph(layout = graph_layout) +
    geom_edge_link(
      aes(alpha = convert_range(weight)),
      colour = "#97a09e", show.legend = FALSE, edge_width = 1.5
    ) +
    geom_node_label(aes(label = name, fill = n), size = 4, alpha = 1) +
    scale_fill_gradient(
      low = "grey", high = "#00EEB1", name = "number of features"
    ) +
    scale_edge_alpha(name = "scaled weight") +
    ggtitle("Pattern Network Among All Pathways")
}

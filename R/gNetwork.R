#' Generate prediction network
#'
#' @description `gNetwork()` generates a prediction network for each functional annotation. For every feature, all other features are considered as independent variables, and the top predictors are selected based on %IncMSE. 
#' 
#' @docType package
#' @name gNetwork
#'
#' @param clusters A list of two; The output of `gClusters()`
#' @param ntop A number. Pick the top n predictors for each feature.
#' @param seed A number of random seed.
#' 
#' @details 
#' We assess relationships between clusters using Mean Squared Error (MSE) changes resulting from random shuffling. `gNetwork()`'s output includes edge weights and node pairs, which are essential inputs for the dashboard.
#' 
#' @examples data(test_data)
#' networkres <- gNetwork(test_cluster, ntop = 3)
#' head(networkres)
#' gNetwork_view(networkres)
#'
#' @importFrom tibble rownames_to_column
#' @importFrom randomForest randomForest importance
#' @export
gNetwork <- function(clusters, ntop = 10, method = "randomforest") {
  clustersres <- clusters[[1]]
  centers <- rownames_to_column(as.data.frame(clustersres$centers), "cluster") |>
    mutate(cluster = paste0("Group_", cluster)) |>
    transpose_dataframe__()

  formula.list <- mass_produce_lm__(centers)
  imp_list <- list()

  for (i in 1:ncol(centers)) {
    if (method == "randomforest") {
      rf <- randomForest(formula.list[[i]], data = centers, proximity = TRUE, importance = TRUE)

      imp_data <- as.data.frame(importance(rf))
      colnames(imp_data)[1] <- "weight"
      imp_data$var_names <- row.names(imp_data)

      imp_data <- imp_data[order(imp_data$weight, decreasing = TRUE), ] |>
        head(ntop) |>
        mutate(
          var_names = factor(var_names, levels = var_names[order(weight)]),
          from = colnames(centers)[i]
        )
      imp_list[[i]] <- imp_data
    }

    if (method == "linear") {
      lm <- lm(formula.list[[i]], data = centers)
      imp_data <- na.omit(as.data.frame(lm$coefficients))
      imp_data$var_names <- rownames(imp_data)
      colnames(imp_data)[1] <- "weight"
      imp_data <- imp_data[-1, ]

      imp_data <- imp_data[order(imp_data$weight, decreasing = TRUE), ] |>
        head(ntop) |>
        mutate(
          var_names = factor(var_names, levels = var_names[order(weight)]),
          from = colnames(centers)[i]
        )
      imp_list[[i]] <- imp_data
    }
  }
  imp_df <- as.data.frame(do.call("rbind", imp_list))
  rownames(imp_df) <- NULL
  imp_df
}

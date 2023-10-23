#' gNetwork
#'
#' @description Generate random forest outputs for the Network.
#'
#' @docType package
#' @name gNetwork
#'
#' @param clusters The output of `gClusters()`
#' @param ntop A number.Pick the top n predictors for each feature.
#' @param seed A number of random seed.
#'
#' @source scale()
#' @examples data(FuncExample)
#' networkres <- gNetwork(b, ntop = 3)
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
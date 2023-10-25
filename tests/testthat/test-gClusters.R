test_that("dataset 'test_data_processed' exists", {
  expect_true(exists('test_data_processed'))
})

test_cluster <- gClusters(test_data_processed,ncluster = 5,elbow.max=15)

test_that("output 1 coerces the kmeans result", {
  expect_equal(class(test_cluster[[1]]),"kmeans")
})

test_that("output 2 coerces the ggplot result and have no NA on the x and y axes", {
  expect_equal(sum(is.na(ggplot_build(test_cluster[[2]])$data[[1]][,1:2])),0)
})



test_that("dataset 'cheesedata' exists", {
  expect_true(exists('cheesedata'))
})

test_that("output 1 coerces the kmeans result", {
  cluschee <- gClusters(cheesedata,ncluster = 10,elbow.max=15)
  expect_equal(class(cluschee[[1]]),"kmeans")
})


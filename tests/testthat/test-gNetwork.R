test_that("data 'test_cluster' exists", {
  expect_true(exists('test_cluster'))
})

test_network <- gNetwork(test_cluster,ntop = 3)

test_that("no missing values", {
  expect_equal(sum(is.na(test_network[,3:4])),0)
})

test_that("colnames match with the required format", {
  expect_equal(colnames(test_network),c("weight","IncNodePurity","var_names","from"))
})

  
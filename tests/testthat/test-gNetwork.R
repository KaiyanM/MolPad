test_that("data 'cluschee' exists", {
  expect_true(exists('cluschee'))
})

networkchee <- gNetwork(cluschee,ntop = 3)

test_that("no missing values", {
  expect_equal(sum(is.na(networkchee)),0)
})

test_that("colnames match with the required format", {
  expect_equal(colnames(networkchee),c("weight","IncNodePurity","var_names","from"))
})

  
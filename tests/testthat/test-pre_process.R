test_that("dataset 'test_data' exists", {
  expect_true(exists('test_data'))
})

test_data_processed <- test_data |>
  pre_process()

test_that("NAs are removed", {
  expect_equal(sum(is.na(test_data_processed)),0)
})

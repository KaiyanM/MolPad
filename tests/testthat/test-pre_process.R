test_that("dataset 'cheese' exists", {
  expect_true(exists('cheese'))
})

cheesedata_test <- head(cheese) |>
  dplyr::mutate(head(annotations["kingdom"])) |>
  dplyr::rename(type=kingdom) |>
  pre_process()

test_that("NAs are removed", {
  expect_equal(sum(is.na(cheesedata_test)),0)
})


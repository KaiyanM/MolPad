data(test_data)
test_that("dataset 'test_data' exists", {
  expect_true(exists('test_data'))
})

test_data_processed <- test_data |>
  pre_process()

test_that("NAs are removed", {
  expect_equal(sum(is.na(test_data_processed)),0)
})

two <- data.frame(
  ID = 1:4,
  A_1 = c(1, 0, 5, 2), A_2 = c(2, 0, 5, 4), A_3 = c(3, 0, 5, 9),
  C_1 = c(10, 1, 7, 3), C_3 = c(30, 5, 7, 3), C_4 = c(20, 2, 7, 8),
  type = c("x", "x", "y", NA)
)
two_spec <- list(A = c("A_1", "A_2", "A_3"), C = c("C_1", "C_3", "C_4"))
two_processed <- pre_process(two, subject_sep = two_spec)

test_that("subjects are scaled separately", {
  a <- as.matrix(two_processed[, two_spec$A])
  cc <- as.matrix(two_processed[, two_spec$C])
  expect_equal(unname(rowMeans(a)), rep(0, nrow(a)))
  expect_equal(unname(rowMeans(cc)), rep(0, nrow(cc)))
  expect_equal(unname(a[1, ]), c(-1, 0, 1))
  expect_equal(unname(cc[1, ]), c(-1, 1, 0))
  expect_equal(sum(is.na(two_processed)), 0)
})

test_that("a flat subject becomes 0 and rows flat in every subject are dropped", {
  expect_equal(two_processed$ID, c(1, 2, 4))
  flat <- two_processed[two_processed$ID == 2, ]
  expect_equal(unname(unlist(flat[, two_spec$A])), c(0, 0, 0))
  expect_true(any(unlist(flat[, two_spec$C]) != 0))
  expect_equal(two_processed$type, c("x", "x", "Other"))
})

test_that("the subject grouping is logged as an attribute", {
  map <- attr(two_processed, "subject_sep")
  expect_equal(map$column, c("A_1", "A_2", "A_3", "C_1", "C_3", "C_4"))
  expect_equal(map$subject, rep(c("A", "C"), each = 3))
  expect_equal(map$time, c("1", "2", "3", "1", "3", "4"))
  expect_null(attr(test_data_processed, "subject_sep"))
})

test_that("string and list forms of subject_sep agree", {
  expect_equal(pre_process(two, subject_sep = "A:A_1-A_3;C:C_1-C_4"), two_processed)
  expect_equal(pre_process(two, subject_sep = "A:A_1,A_2,A_3; C:C_1,C_3-C_4"), two_processed)
})

test_that("bad subject_sep is rejected", {
  expect_error(pre_process(two, subject_sep = "A:A_1-A_9;C:C_1-C_4"), "unknown column")
  expect_error(pre_process(two, subject_sep = list(A = two_spec$A)), "does not cover")
  expect_error(pre_process(two, subject_sep = "A:A_1-A_3;C:A_3-C_4"), "more than one subject")
  expect_error(pre_process(two, subject_sep = "A_1-A_3"), "must look like")
  expect_error(pre_process(two, subject_sep = "A:A_1-A_3;B:C_1;C:C_3-C_4"), "at least two")
})

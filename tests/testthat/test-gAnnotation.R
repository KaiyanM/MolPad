data(test_data)
test_that("dataset 'test_annotations' exists", {
  expect_true(exists('test_annotations'))
})

test_annotations_processed <- gAnnotation(test_annotations,system,class)

test_that("NAs in the annotation are replaced with Unknown", {
  expect_equal(sum(is.na(test_annotations_processed$Pathway),is.na(test_annotations_processed$taxonomic.scope)),0)
})

test_that("the original column names are kept", {
  expect_equal(attr(test_annotations_processed, "molpad_levels"), list(level1 = "system", level2 = "class"))
  quoted <- gAnnotation(test_annotations, "system", "class")
  expect_equal(attr(quoted, "molpad_levels"), list(level1 = "system", level2 = "class"))
})

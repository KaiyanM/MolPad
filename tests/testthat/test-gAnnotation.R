data(test_data)
test_that("dataset 'test_annotations' exists", {
  expect_true(exists('test_annotations'))
})

test_annotations_processed <- gAnnotation(test_annotations,system,class)

test_that("NAs in the annotation are replaced with Unknown", {
  expect_equal(sum(is.na(test_annotations_processed$Pathway),is.na(test_annotations_processed$taxonomic.scope)),0)
})

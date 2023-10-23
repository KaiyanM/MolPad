test_that("dataset 'annotations' exists", {
  expect_true(exists('annotations'))
})

pathchee <- gAnnotation(annotations,phylum,class)

test_that("NAs are replaced with Unknown", {
  expect_equal(sum(is.na(pathchee$Pathway),is.na(pathchee$taxonomic.scope)),0)
})
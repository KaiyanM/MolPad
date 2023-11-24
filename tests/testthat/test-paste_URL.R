
links <- paste_URL(test_annotations_processed$KEGG_ID,"KEGG")
  
test_that("force to separate multiple IDs", {
  expect_equal(links[74],"<a href='https://www.kegg.jp/entry/K05373' target='_blank'>K05373</a><br/><a href='https://www.kegg.jp/entry/K18926' target='_blank'>K18926</a>")
})

test_that("do not paste links if there are NAs", {
  expect_equal(links[2],"NA")
})

test_that("the processed vector has equal length with the original column", {
  expect_equal(length(links),nrow(test_annotations_processed))
})
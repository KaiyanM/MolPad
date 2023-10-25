reshaped <- reshape_for_make_functions(test_data_processed, 
                           test_cluster, 
                           test_annotations_processed, 
                           id_colname = c("GO_ID","KEGG_ID"),
                           id_type = c("GO","KEGG"))

test_that("output is a list of 3", {
  expect_equal(length(reshaped),3)
})

test_that("the first dataset contains ID and cluster", {
  expect_equal(colnames(reshaped[[1]])[1:2],c("ID","cluster"))
})

test_that("the second dataset contains the following columns: ID,type,cluster,day,value,taxonomic.scope", {
  expect_equal(colnames(reshaped[[2]]),c('ID','type','cluster','day','value','taxonomic.scope'))
})



data("test_data", package = "MolPad", envir = environment())

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


test_that("subjects logged by pre_process() become a facet column on a shared time axis", {
  processed <- pre_process(test_data, subject_sep = list(first = paste0("T", 1:5),
                                                       second = paste0("T", c(6, 8, 9, 10, 7))))
  expect_equal(nrow(processed), nrow(test_data_processed))
  long <- reshape_for_make_functions(processed, test_cluster, test_annotations_processed,
                                     id_colname = NULL, id_type = NULL)[[2]]
  expect_equal(colnames(long), c('ID','type','cluster','day','value','subject','taxonomic.scope'))
  expect_equal(nrow(long), nrow(reshaped[[2]]))
  expect_equal(levels(long$subject), c("first", "second"))
  expect_equal(levels(long$day), as.character(1:5))
  expect_equal(as.character(long$day[1:10]), as.character(c(1:5, 1, 5, 2, 3, 4)))
  expect_equal(as.character(long$subject[1:10]), rep(c("first", "second"), each = 5))
  expect_s3_class(make_line_plot(long, "Group_1", unique(long$taxonomic.scope)), "ggplot")
})

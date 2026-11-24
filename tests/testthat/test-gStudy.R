data("test_data", package = "MolPad", envir = environment())

study <- gStudy(
  background = "A made-up study.",
  feature = "protein",
  samples = list(groups = list(first = "the control", second = "treated; day 3 was repeated"),
                 time = "day of sampling"),
  level1 = "system",
  level2 = list(column = "class", about = "who carries it"),
  colour = "kind",
  ids = c(GO_ID = "GO", KEGG_ID = "KEGG"))

test_that("gStudy() writes the short forms out", {
  expect_s3_class(study, "molpad_study")
  expect_equal(study$feature, list(name = "protein"))
  expect_equal(study$level1, list(column = "system", name = "system"))
  expect_equal(study$level2$about, "who carries it")
  expect_equal(study$samples$time, list(about = "day of sampling"))
  expect_equal(study$ids$KEGG_ID, list(type = "KEGG"))
  expect_error(gStudy(samples = list(desing = "typo")), "desing")
  one <- gStudy(samples = list(groups = "Two batches.", time = "Days, aligned."))
  expect_equal(one$samples, list(groups = "Two batches.", time = list(about = "Days, aligned.")))
  expect_equal(gStudy(samples = "Two batches.")$samples$groups, "Two batches.")
  expect_output(print(one), "Two batches.")
  expect_error(as_study__(list(sample = "typo")), "sample")
  expect_output(print(study), "MolPad study")
  expect_output(print(study), "treated; day 3 was repeated")
})

test_that("a study can be saved and read back", {
  file <- tempfile(fileext = ".json")
  write_study(study, file)
  expect_equal(gStudy(file = file), study)
  expect_equal(as_study__(file), study)
})

test_that("sample groups are read from the column names", {
  expect_equal(detect_subjects__(c("A_1", "A_2", "A_3", "C_1", "C_3")),
               list(A = c("A_1", "A_2", "A_3"), C = c("C_1", "C_3")))
  expect_equal(names(detect_subjects__(c("liver.1", "liver.2", "soft_cheese-1", "soft_cheese-2"))),
               c("liver", "soft_cheese"))
  expect_null(detect_subjects__(paste0("T", 1:10)))             # no group in the names
  expect_null(detect_subjects__(c("A_1", "A_2")))               # one group only
  expect_null(detect_subjects__(c("A_1", "C_1", "A_2", "C_2"))) # groups not side by side
  expect_null(detect_subjects__(c("A_1", "A_2", "C_1", "week")))
})

test_that("pre_process() takes the colour column and the sample groups from the study", {
  raw <- test_data
  colnames(raw)[2:11] <- c(paste0("first_", 1:5), paste0("second_", 1:5))
  colnames(raw)[colnames(raw) == "type"] <- "kind"
  raw <- raw[, c("ID", "kind", setdiff(colnames(raw), c("ID", "kind")))]   # the colour column is not last
  out <- pre_process(raw, study = study)
  expect_equal(colnames(out)[c(1, ncol(out))], c("ID", "type"))
  map <- attr(out, "subject_sep")
  expect_equal(unique(map$subject), c("first", "second"))
  expect_equal(map$time, rep(as.character(1:5), 2))
  expect_identical(attr(out, "molpad_study"), study)

  # the same result as writing the groups out
  by_hand <- pre_process(raw[, c(setdiff(colnames(raw), "kind"), "kind")] |> dplyr::rename(type = kind),
                         subject_sep = "first:first_1-first_5;second:second_1-second_5")
  expect_equal(as.data.frame(out), as.data.frame(by_hand), ignore_attr = TRUE)

  # columns given in the study win over the names; without a study nothing is detected
  split <- gStudy(samples = list(columns = list(x = paste0("first_", 1:5), y = paste0("second_", 1:5))), colour = "kind")
  expect_equal(unique(attr(pre_process(raw, study = split), "subject_sep")$subject), c("x", "y"))
  expect_null(attr(pre_process(test_data), "subject_sep"))
  expect_null(attr(pre_process(test_data, study = gStudy(feature = "protein")), "subject_sep"))
})

test_that("gAnnotation() takes the level columns from the study", {
  ann <- gAnnotation(test_annotations, study = study)
  expect_equal(ann$Pathway, gAnnotation(test_annotations, system, class)$Pathway)
  expect_equal(attr(ann, "molpad_levels"), list(level1 = "system", level2 = "class"))
  expect_identical(attr(ann, "molpad_study"), study)
  expect_error(gAnnotation(test_annotations), "study")
  expect_error(gAnnotation(test_annotations, study = gStudy(level1 = "nope", level2 = "class")), "nope")
})

test_that("the study written first reaches the page without being passed again", {
  raw <- test_data
  colnames(raw)[2:11] <- c(paste0("first_", 1:5), paste0("second_", 1:5))
  data <- pre_process(raw, study = study)
  ann <- gAnnotation(test_annotations, study = study)
  cl <- test_cluster
  cl[[1]]$cluster <- cl[[1]]$cluster[seq_len(nrow(data))]
  p <- d3_payload(data, cl, ann, test_network)
  d <- p$dataset
  expect_equal(names(p$id_links), c("GO_ID", "KEGG_ID"))        # from study$ids
  expect_equal(d$level1$source, "system")
  expect_equal(d$level2$about, "who carries it")
  expect_equal(d$samples$groups$second, "treated; day 3 was repeated")
  expect_equal(d$samples$time$about, "day of sampling")
  expect_null(d$samples$columns)
  expect_equal(vapply(p$subjects, function(s) s$name, ""), c("first", "second"))
  sentence <- gStudy(samples = list(groups = "Two batches of anything."))
  expect_equal(d3_payload(data, cl, ann, test_network, study = sentence)$dataset$samples$groups,
               "Two batches of anything.")
  wrong <- gStudy(samples = list(groups = list(third = "?")))
  expect_error(d3_payload(data, cl, ann, test_network, study = wrong), "third")
})

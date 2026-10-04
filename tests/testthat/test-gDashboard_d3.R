data("test_data", package = "MolPad", envir = environment())

payload <- d3_payload(test_data_processed,
                      test_cluster,
                      test_annotations_processed,
                      test_network,
                      dashboardtitle = "Test",
                      id_colname = c("GO_ID", "KEGG_ID"),
                      id_type = c("GO", "KEGG"))

test_that("payload has every key of the JSON contract", {
  expect_named(payload, c("schema_version", "title", "timepoints", "subjects", "time_labels",
                          "types", "taxa",
                          "pathways", "clusters", "annotation_columns", "id_links",
                          "features", "edges", "weight_slider"))
  expect_equal(payload$title, "Test")
  expect_equal(payload$schema_version, 2L)
  expect_length(payload$subjects, 0)
  expect_equal(as.character(payload$time_labels), paste0("T", 1:10))
  expect_equal(as.character(payload$timepoints), paste0("T", 1:10))
  expect_equal(as.character(payload$types), c("type_A", "type_B", "type_C", "type_D"))
  expect_equal(as.character(payload$clusters), paste0("Group_", 1:5))
  expect_equal(as.character(payload$annotation_columns),
               c("GO_ID", "KEGG_ID", "Pathway", "taxonomic.scope"))
})

test_that("features carry one value per timepoint and the cluster label", {
  f <- payload$features
  expect_equal(nrow(f), 100)
  expect_true(is.character(f$ID))
  expect_true(all(lengths(f$values) == 10))
  expect_true(all(f$cluster %in% paste0("Group_", 1:5)))
  expect_equal(f$values[[1]], unname(unlist(test_data_processed[1, 2:11])))
  expect_equal(f$cluster, paste0("Group_", test_cluster[[1]]$cluster))
  expect_equal(f$taxonomic.scope, test_annotations_processed$taxonomic.scope)
})

test_that("edges keep every gNetwork row and turn NaN into NA", {
  e <- payload$edges
  expect_equal(nrow(e), nrow(test_network))
  expect_equal(sum(is.na(e$weight)), sum(is.nan(test_network$weight)))
  expect_false(any(is.nan(e$weight)))
  expect_equal(e$to, as.character(test_network$var_names))
})

test_that("slider defaults match gDashboard()", {
  q <- quantile(abs(test_network$weight), na.rm = TRUE)
  expect_equal(payload$weight_slider$max, round(unname(q[4]), 1))
  expect_equal(payload$weight_slider$value, round(unname(q[3]), 1))
  expect_equal(payload$weight_slider$min, 0)
})

test_that("link templates follow paste_URL()", {
  expect_named(payload$id_links, c("GO_ID", "KEGG_ID"))
  expect_equal(payload$id_links$GO_ID$url, "https://www.ebi.ac.uk/QuickGO/term/{id}")
  expect_equal(payload$id_links$GO_ID$pattern, "GO:\\d{7}")
  expect_equal(payload$id_links$KEGG_ID$url, "https://www.kegg.jp/entry/{id}")
  expect_equal(payload$id_links$KEGG_ID$pattern, "K\\d{5}")
  expect_length(d3_link_templates(NULL, NULL), 0)
  expect_error(d3_link_templates(c("a", "b"), "GO"), "same length")
  expect_error(d3_link_templates("a", "Pfam"), "GO")
})

test_that("payload validation catches bad inputs", {
  expect_error(d3_payload(test_data_processed[, -12], test_cluster,
                          test_annotations_processed, test_network), "type")
  expect_error(d3_payload(test_data_processed, test_cluster,
                          test_annotations_processed[, -5], test_network), "taxonomic.scope")
  expect_error(d3_payload(test_data_processed[1:10, ], test_cluster,
                          test_annotations_processed, test_network), "one entry per row")
})

test_that("JSON is valid, free of NaN and safe inside a script tag", {
  json <- d3_payload_json(payload)
  expect_true(jsonlite::validate(json))
  expect_false(grepl("NaN", json, fixed = TRUE))
  expect_true(grepl('"weight":null', json, fixed = TRUE))
  expect_true(grepl('"timepoints":["T1"', json, fixed = TRUE))

  back <- jsonlite::fromJSON(json)
  expect_equal(back$features$values[[1]], unname(unlist(test_data_processed[1, 2:11])))
  expect_equal(back$features$ID[1:3], c("1", "2", "3"))

  no_links <- d3_payload(test_data_processed, test_cluster,
                         test_annotations_processed, test_network)
  expect_true(grepl('"id_links":{}', d3_payload_json(no_links), fixed = TRUE))

  evil <- d3_payload(test_data_processed, test_cluster, test_annotations_processed,
                     test_network, dashboardtitle = "x</script>y")
  expect_true(grepl("x<\\/script>y", d3_payload_json(evil), fixed = TRUE))
})

test_that("single-element vectors still serialise as arrays", {
  one <- payload
  one$pathways <- I("only")
  expect_true(grepl('"pathways":["only"]', d3_payload_json(one), fixed = TRUE))
})

test_that("gDashboard_d3 writes a self-contained page", {
  out <- tempfile("molpad_d3_test_")
  path <- gDashboard_d3(test_data_processed, test_cluster, test_annotations_processed,
                        test_network, dashboardtitle = "A <b>&",
                        id_colname = c("GO_ID", "KEGG_ID"), id_type = c("GO", "KEGG"),
                        output_dir = out, open = FALSE)
  expect_true(file.exists(path))
  html <- paste(readLines(path, warn = FALSE, encoding = "UTF-8"), collapse = "\n")
  expect_true(grepl('id="molpad-data"', html, fixed = TRUE))
  expect_true(grepl("<title>A &lt;b&gt;&amp;</title>", html, fixed = TRUE))
  expect_true(grepl("https://d3js.org", html, fixed = TRUE))
  manifest <- jsonlite::fromJSON(file.path(d3_asset_dir(), "manifest.json"))
  for (js in manifest$js) {
    expect_true(grepl(paste0("<!-- molpad:", js, " -->"), html, fixed = TRUE), label = js)
  }
  expect_false(grepl('<script src=', html, fixed = TRUE))
})

test_that("gDashboard_d3 can write a multi-file bundle", {
  out <- tempfile("molpad_d3_test_")
  path <- gDashboard_d3(test_data_processed, test_cluster, test_annotations_processed,
                        test_network, output_dir = out, open = FALSE,
                        self_contained = FALSE)
  expect_true(all(dir.exists(file.path(out, c("js", "css", "lib")))))
  expect_true(file.exists(file.path(out, "js", "app.js")))
  html <- paste(readLines(path, warn = FALSE, encoding = "UTF-8"), collapse = "\n")
  expect_true(grepl('<script src="js/app.js"></script>', html, fixed = TRUE))
  expect_true(grepl('<link rel="stylesheet" href="css/dashboard.css">', html, fixed = TRUE))
  expect_true(grepl('id="molpad-data"', html, fixed = TRUE))
})

test_that("subjects from pre_process() are passed to the page", {
  spec <- list(A = c("A_1", "A_2", "A_3", "A_4", "A_5"), C = c("C_1", "C_3", "C_4", "C_5", "C_6"))
  two <- test_data
  colnames(two)[2:11] <- unlist(spec)
  processed <- pre_process(two, subject_sep = spec)
  p <- d3_payload(processed, test_cluster, test_annotations_processed, test_network)
  expect_equal(as.character(p$timepoints), unname(unlist(spec)))
  expect_equal(as.character(p$time_labels), as.character(1:6))
  expect_equal(vapply(p$subjects, function(s) s$name, ""), c("A", "C"))
  expect_equal(as.character(p$subjects[[2]]$columns), spec$C)
  expect_equal(as.character(p$subjects[[2]]$labels), c("1", "3", "4", "5", "6"))
  expect_true(all(lengths(p$features$values) == 10))

  json <- d3_payload_json(p)
  expect_true(grepl('"subjects":[{"name":"A","columns":["A_1"', json, fixed = TRUE))
  expect_true(grepl('"subjects":[]', d3_payload_json(payload), fixed = TRUE))
})

setwd("/Users/hazelma/Documents/GitHub/MolPad")
usethis::use_testthat(3)

use_r()
use_test("pre_process.R")
use_test("gClusters.R")
use_test("gAnnotation.R")
use_test("gNetwork")
use_test("gDashboard.R") # removed
use_test("reshape_for_make_functions") 
use_test("paste_URL")
devtools::test()

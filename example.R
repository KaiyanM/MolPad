#-----------------------update package----------------------
library(devtools)

setwd("/Users/hazelma/Documents/GitHub")
document("MolPad") #important: generate man

install("MolPad")
library("MolPad")

#-----------------------run example----------------------
data("test_data")

gDashboard(test_data_processed,test_cluster,test_annotations_processed,test_network,
           dashboardtitle = "Test",
           id_colname = c("GO_ID","KEGG_ID"),id_type = c("GO","KEGG"))


setwd("/Users/hazelma/Documents/GitHub/MolPad")
devtools::test()
devtools::check()
#-----------------------run example----------------------
data("cheese")

#-----------------------generate web----------------------
library(pkgdown)
#----
setwd("/Users/hazelma/Documents/GitHub/MolPad")
pkgdown::clean_site()
pkgdown::build_site()
#----

convert_range(5:10)



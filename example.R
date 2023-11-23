#-----------------------update package----------------------
library(devtools)

setwd("/Users/hazelma/Documents/GitHub")
document("MolPad") #important: generate man


install("MolPad")
library("MolPad")

data("test_data")
library(shiny) #br()

gDashboard(test_data_processed,test_cluster,test_annotations_processed,test_network,
           dashboardtitle = "Test",
           id_colname = c("GO_ID","KEGG_ID"),id_type = c("GO","KEGG"))

# add readme on installation
# add screenshot for nevigation
#-----------------------update package----------------------
library(devtools)

#setwd("/Users/hazelma/Documents/GitHub")
#setwd("D:/GitHub/MolPad")
setwd("D:/GitHub")

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

library(dplyr)
cheesedata <- cheese |> 
  select(ID, A_1:C_5, phylum) |> 
  rename(type=phylum) |> 
  pre_process(subject_sep = "A:A_1-A_5;C:C_1-C_5")

pathchee <- gAnnotation(annotations,"phylum","class")
cluschee <- gClusters(cheesedata,ncluster = 10,elbow.max=15)
networkchee <- gNetwork(cluschee,ntop = 3)

gDashboard(cheesedata,
           cluschee,
           pathchee,
           networkchee,
           id_colname = c("GO_ID","KEGG_ID"),
           id_type = c("GO","KEGG"))



#-----------------------generate web----------------------
library(pkgdown)
#----
#setwd("/Users/hazelma/Documents/GitHub/MolPad")
setwd("D:/GitHub/MolPad")
pkgdown::clean_site()
pkgdown::build_site()
#----

convert_range(5:10)

#---------

remove.packages("MolPad")
devtools::install("D:/GitHub/MolPad")

#
devtools::load_all("D:/GitHub/MolPad")
#.rs.restartR()


devtools::install("D:/GitHub/MolPad")



data(test_data)
gDashboard_d3(test_data_processed, test_cluster, test_annotations_processed,
              test_network, dashboardtitle = "Test",
              id_colname = c("GO_ID", "KEGG_ID"), id_type = c("GO", "KEGG"))

gDashboard_d3(cheesedata,
           cluschee,
           pathchee,
           networkchee,
           id_colname = c("GO_ID","KEGG_ID"),
           id_type = c("GO","KEGG"))

gDashboard_d3(cheesedata,
              cluschee,
              pathchee,
              networkchee,
              id_colname = c("GO_ID","KEGG_ID"),
              id_type = c("GO","KEGG"),
              output_dir = "D:/GitHub/MolPad/dashboards/cheese")

#python -m agent.serve --dashboard /mnt/d/GitHub/MolPad/dashboards/cheese/index.html                         --context agent/contexts/cheese.json

write.csv(cheesedata,"cheesedata.csv")
write.csv(pathchee,"pathchee.csv")
write.csv(networkchee,"networkchee.csv")
class(cluschee[[1]])

km <- cluschee[[1]]
write.csv(km$centers, "cluschee_centers.csv")
write.csv(
  data.frame(cluster = km$cluster),
  "cluster_labels.csv",
  row.names = FALSE
)

library(jsonlite)
jsonlite::write_json(
  list(
    totss = km$totss,
    tot.withinss = km$tot.withinss,
    betweenss = km$betweenss,
    size = km$size,
    iter = km$iter,
    k = nrow(km$centers)
  ),
  "model_metadata.json",
  auto_unbox = TRUE,
  pretty = TRUE
)

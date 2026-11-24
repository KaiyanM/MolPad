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

# The study is written first: which columns are what, and what they mean. The steps below read
# it, so the sample groups, the level columns and the id columns are not repeated.
study <- gStudy(
  background = "Metagenomic data from the surface of two washed-rind cheeses, sampled over ripening.",
  feature = "contig",                          # optional: what one row is called
  # the value columns A_1 ... C_5: the groups A and C are read from the column names
  samples = list(groups = "Two kinds of cheese, A and C.",
                 time = "Sampling time points during ripening, aligned between the cheeses but with missing ones."),
  level1 = list(column = "phylum", about = "the phylum a contig is assigned to"),
  level2 = list(column = "class", about = "the class within that phylum"),
  colour = "phylum",                           # becomes the `type` column
  ids = c(GO_ID = "GO", KEGG_ID = "KEGG"))
# write_study(study, "agent/contexts/cheese.json")   # the same, as a file

cheesedata <- cheese |> 
  select(ID, A_1:C_5, phylum) |> 
  pre_process(study = study)

pathchee <- gAnnotation(annotations, study = study)
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
              # the study travels with cheesedata: it gives the id columns, the labels of the
              # page and what the agent is told about the data
              output_dir = "D:/GitHub/MolPad/dashboards/cheese")

#python -m agent.serve --dashboard /mnt/d/GitHub/MolPad/dashboards/cheese/index.html
# (the study is in the page; --context <study.json> overrules it)

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

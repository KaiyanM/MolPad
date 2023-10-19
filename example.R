#-----------------------update package----------------------
library(devtools)

setwd("/Users/hazelma/Documents/GitHub")
#create("MolPad")
document("MolPad") #important: generate man


install("MolPad")
library("MolPad")

#-----------------------run fungal garden----------------------
data("fungal_garden")

a <- pre_process(fungal_dlist,typenameList = c("Peptide","Metabolite","Lipid"))
b <- gClusters(a,ncluster = 15)

networkres <- gNetwork(b,ntop = 5)

pathway <- gAnnotation(pathway,Pathway,taxonomic.scope,ko_term)

gDashboard(a,b,pathway,networkres,dashboardtitle = "MolPad Dashboard","KEGG")

#-----------------------run cheese----------------------
#-------- process cheese12 data--------

chee <- merge(c12,t12[,c("ID","kingdom")],by="ID")
colnames(chee)[12] <- 'type'
chee$type[is.na(chee$type)] <- "Other"
chee[,1:11] <- scale_by_row__(chee[,1:11])

#if the number does not change, then remove the feature
chee <- na.omit(chee)

#----------------------
cluschee <- gClusters(chee,ncluster = 10,elbow.max=15)
networkchee <- gNetwork(cluschee,ntop = 3)

pathchee <- merge(f12,t12,by="ID") %>%
  rename("taxonomic.scope" = "phylum") %>%
  rename("Pathway" = "kingdom")


gDashboard(chee,cluschee,pathchee,networkchee,dashboardtitle = "Test","KEGG_ID")

#-----



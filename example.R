#-----------------------update package----------------------
library(devtools)


create("MolPad")
document("MolPad") #important: generate man


install("MolPad")
library("MolPad")

#-----------------------run fungal garden----------------------
data("fungal_garden")
a <- pre_process(fungal_dlist,typenameList = c("Peptide","Metabolite","Lipid"))
b <- gClusters(a,ncluster = 15)

networkres <- gNetwork(b,ntop = 5)
b[[2]]
gNetwork_view(networkres)
networkres
gDashboard(a,b,pathway,networkres,dashboardtitle = "MolPad Dashboard","ko_term")

#-----------------------run cheese----------------------


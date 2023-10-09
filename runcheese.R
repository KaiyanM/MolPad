#-----------------------update package----------------------
library(devtools)
dirname(getwd())
setwd("/Users/hazelma/Documents/GitHub/fungal_garden_interactome")

document("pkg") #important: generate man
#install("pkg")
library("pkg")

#-------- load data--------
data("cheese")

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

library(dplyr)
pathchee <- merge(f12,t12,by="ID") %>%
  rename("taxonomic.scope" = "phylum") %>%
  rename("Pathway" = "kingdom")




#((((((((((((((((((((((((((((((((()))))))))))))))))))))))))))))))))

#run this

gDashboard(chee,cluschee,pathchee,networkchee,dashboardtitle = "Test","KEGG_ID")


#((((((((((((((((((((((((((((((((()))))))))))))))))))))))))))))))))






#other
ptw_process(pathchee,"Other_ID")

make_the_graph(pathchee,networkchee,min_weight = 0.3,s_ptw="Eukaryota")

#______________

ptw<- gPathway(pathchee,chee,cluschee)
dfgroup_long <- gMainData(chee,cluschee,ptw)

nao_ptw <- ptw_process(ptw,"Other_ID")
uni_t <- unique(dfgroup_long$taxonomic.scope)
uni_ptw <- unique(nao_ptw$Pathaway)

make_the_graph(ptw,networkchee, 0,"Bacteria") #NA

#Eukaryota cannot run
#%%%%%%


#make res
data <- data.frame("from"=network_output$from,"to" = network_output$Var.Names,"weight"=abs(network_output$weight))
#make ncluster
ncluster <- length(unique(network_output$from))
#-----------------------------------------------
#since nao_ptw is processed in gDashboard, use ptw

count_group <- ptw[ptw$Pathway == s_ptw,] %>% count(cluster, sort = TRUE)

if(nrow(count_group) < ncluster){
  missing_group <- unique(data$from)[!(unique(data$from) %in% count_group$cluster)]
  count_group <- rbind(count_group,data.frame(cluster=missing_group,n=rep(0,length(missing_group))))
}

g <- filter(data,weight>min_weight) %>%
  graph_from_data_frame(directed=FALSE, vertices=count_group)

set.seed(2017)
g %>%
  ggraph(layout = 'kk') +
  geom_edge_link(alpha=0.7,aes(width = weight),color = "#97A09E") +
  geom_node_label(aes(label=name,fill = n),size=4,alpha= 1)+
  scale_fill_gradient(low = "grey", high = "#00EEB1")+
  ggtitle("Pattern Network Among All Pathways")


#^^^^^^^^old_____________________________________________________


data <- data.frame("from"=networkchee$from,"to" = networkchee$Var.Names,"weight"=networkchee$weight)
#make ncluster
ncluster <- length(unique(networkchee$from))
#-----------------------------------------------
#since nao_ptw is processed in gDashboard, use ptw??? here we shold omit na

##
ptw <- ptw[!is.na(ptw$Pathway),]
##

count_group <- ptw[ptw$Pathway == "Eukaryota",] %>% count(cluster, sort = TRUE)

unique(ptw$Pathway)


if(nrow(count_group) < ncluster){
  missing_group <- unique(data$from)[!(unique(data$from) %in% count_group$cluster)]
  count_group <- rbind(count_group,data.frame(cluster=missing_group,n=rep(0,length(missing_group))))
}

g <- filter(data,weight>0.1) %>%
  graph_from_data_frame(directed=FALSE, vertices=count_group)

set.seed(2017)
g %>%
  ggraph(layout = 'kk') +
  geom_edge_link(alpha=0.7,color = "#97A09E") +
  geom_node_label(aes(label=name,fill = n),size=4,alpha= 1)+
  scale_fill_gradient(low = "grey", high = "#00EEB1")+
  ggtitle("Pattern Network Among All Pathways")


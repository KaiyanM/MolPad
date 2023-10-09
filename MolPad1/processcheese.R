# Cheese Data

#-------- load data--------
setwd("/Users/hazelma/Documents/GitHub/fungal_garden_interactome")
Cheese_data_quant_norm <- readRDS(paste0(getwd(),"/Cheeseupdate/Cheese_data_quant_norm.rds"))

Cheese_data <- readRDS(paste0(getwd(),"/Cheeseupdate/Cheese_data.rds"))
Functions_annoations <- readRDS(paste0(getwd(),"/Cheeseupdate/Functions_annoations.rds"))
Taxonomy_annoations <- readRDS(paste0(getwd(),"/Cheeseupdate/Taxonomy_annoations.rds"))

Cheese_data2 <- readRDS(paste0(getwd(),"/Cheese_data_rep2/Cheese_data_rep2.rds"))
Functions_annoations2 <- readRDS(paste0(getwd(),"/Cheese_data_rep2/Functions_annoations_rep2.rds"))
Taxonomy_annoations2 <- readRDS(paste0(getwd(),"/Cheese_data_rep2/Taxonomy_annoations.rds"))


Cheese_data_rep2
#summary(as.factor(Taxonomy_annoations$kingdom))
#summary(as.factor(Taxonomy_annoations$phylum))

library("pkg")
#-----------------------merge----------------------

# problem: data duplicate
## removed
a1 <- cbind(Functions_annoations,Taxonomy_annoations[,-1])
a2 <- cbind(Functions_annoations2,Taxonomy_annoations2[,-1])

a1$paste <- do.call(paste, c(a1[2:10], sep = "_"))
a2$paste <- do.call(paste, c(a2[2:10], sep = "_"))

a1 <- a1[!duplicated(a1$paste),]
a2 <- a2[!duplicated(a2$paste),]

inter12 <- intersect(a1$paste,a2$paste) %>% as.vector()

a1 <- filter(a1, paste %in% inter12)
a2 <- filter(a2, paste %in% inter12)

idname2 <- a2 %>%
  filter(paste %in% inter12) %>%
  select(ID,paste) %>%
  rename(ID2 = ID)

idname1 <- a1 %>%
  filter(paste %in% inter12) %>%
  select(ID,paste) %>%
  rename(ID1 = ID)

idname <- merge(idname1,idname2)

colnames(Cheese_data2) <- c("ID2",6:10)

c2 <- merge(Cheese_data2,idname[,2:3])[,-1]
colnames(c2)[6] <- "ID"
c1 <- Cheese_data[Cheese_data$ID %in% idname$ID1,]
c12 <- na.omit(merge(c1,c2,by='ID'))
colnames(c12)[2:11] <- c(paste0("A",1:5),paste0("B",1:5))

f12 <- Functions_annoations[Functions_annoations$ID %in% idname$ID1,]
t12 <- Taxonomy_annoations[Taxonomy_annoations$ID %in% idname$ID1,]

save(c12,f12,t12, file = "cheese12.rdata")

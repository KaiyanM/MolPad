---
title: 'MolPad: An R-Shiny Package for Cluster Co-Expression Analysis in Longitudinal Microbiomics'
tags:
  - R
  - shiny
  - multi-omics
  - visualization
  - cluster analysis
  - network
authors:
  - name: Kaiyan Ma
    orcid: 0000-0002-7355-8924
    equal-contrib: true
    affiliation: 1
  - name: Author Without ORCID
    equal-contrib: true # (This is how you can denote equal contributions between multiple authors)
    affiliation: "1, 2" # (Multiple affiliations must be quoted)
  - name: Author with no affiliation
    corresponding: true # (This is how to denote the corresponding author)
    affiliation: 3
affiliations:
 - name: University of Wisconsin-Madison, USA
   index: 1
 - name: Institution Name, Country
   index: 2
date: 18 November 2023
bibliography: paper.bib

# Optional fields if submitting to a AAS journal too, see this blog post:
# https://blog.joss.theoj.org/2018/12/a-new-collaboration-with-aas-publishing
aas-doi: 10.3847/xxxxx <- update this with the DOI from AAS once you know it.
aas-journal: Astrophysical Journal <- The name of the AAS journal.
---

# Summary

The R-shiny package MolPad provides an interactive dashboard for understanding the dynamics of longitudinal molecular co-expression in microbiomics. The main idea for addressing the issue is first to use a network to overview major patterns among their predictive relationships and then zoom into specific clusters of interest. It is designed with a focus-plu-context analysis strategy and automatically generates links to online curated annotations. The dashboard consists of a cluster-level network, a bar plot of taxonomic composition, a line plot of data modalities, and a table for each pathway, as illustrated in Fig \ref{fig:dashboard}. Plus, the package includes functions that handle the data processing for creating the dashboard. This makes it beginner-friendly for users with less R programming experience. We illustrate these methods with a case study on a longitudinal, multi-platform meta-genomics analysis for cheese communities.

# Statement of need

The realm of microbiomics is expanding rapidly, with numerous new studies and methodologies emerging. This highlights the need for visualizations that can account for differences across modalities. It’s also important to enable interpretations of dynamics and network structure because these have specific meanings in the genomic context. Another issue is the annotation. The special modality characteristic of microbiomics determines that each identical feature can be classified with various taxons and could have several IDs in different databases. Therefore, although the annotation is available online, it can be tedious to search for parts manually. Moreover, most present visualizations poorly evaluate longitudinal change across microbiomes. In longitudinal data, we need to gain insight into the functioning of how individual features change and how they may influence related features. Thus, it depends upon analysis within one table and across tables. All of these have posed a challenge for unified visualization and interpretation. 

In response to the above issues, previous studies on interactive visualization tools have designed methods to work on such data. `microViz` [@microviz] provides a Shiny app for interactive exploration by pairing ordination plots and composition circular bar charts to show each taxon's prevalence and abundance. `GWENA` [@Lemoine_Scott-Boyer_Ambroise_Périn_Droit_2021] applies a network in conducting gene co‑expression analysis and extended module characterization in a single package to understand the underlying processes contributing to a disease or a phenotype. `NeVOmics` [@Zúñiga-León_Carrasco-Navarro_Fierro_2018] improved compatibility with a dynamic dashboard and facilitated the functional characterization of data from omics technologies. It also integrates Over-representation analysis methodology and network-based visualization to show the enrichment results. These methods suggest the mechanisms that improve the utility of microbiomics visualization tools under analysis.

# Methods

To depict the longitudinal changes, we first scale and cluster trajectories across all molecular features and then reorganize the clusters into a network graph. We use K-means and a built-in elbow method to choose the optimal number of clusters. Then, we take the centers of each cluster and run a random forest regression for each centroid with all the other centroids as predictors. We pick the top n predictors to build a cluster network with the Mean Decrease Accuracy as the feature importance. Based on the random forest prediction, if two groups of features are highly linked according to the network, they will have strongly related longitudinal patterns, as shown in Fig \ref{fig:pattern}.

# Case Study: Cheese Data

Here we aim to highlight the versatility of the MolPad Dashboard with a case study of microbial communities on the wash-rind cheese' surface collected during cheese ripening[@doi:10.1128/msystems.00701-22]. This data stands for a general case that only includes single-omic measurements for the change of Bacteria or Eukaryota in each cheese sample. It has multiple nested annotation labels ranging from kingdom to class, making it more flexible in interpretation. 

Our goal is to verify their conclusions and provide an alternative to visualize complicated longitudinal data. According to the study, in the bacterial community, Firmicutes are dominant at the very beginning, and Proteobacteria quickly take over the domination by the end of ripening. Overall, cheeses A and C show a reproducible establishment of Actinobacteria and Bacteroidetes separately. To confirm the mentioned findings using the MolPad dashboard, we examined two cheeses (A and C) across all three batches during weeks 2 to 13.

In applying the dashboard, we made an extended time series by connecting the last time point of cheese A with the first one of cheese C. This allowed us to track unusual pattern combinations among different species and stages. We take the top four groups from the bacterial community for detailed analysis in Fig \ref{fig:cheesecase}. Overall, our results match the above research and could be used to provide intuitive explanations in supporting the findings, which substantiate the capabilities of `MolPad` as a reproducible tool to streamline the visualization of longitudinal patterns for the timely implementation of high-dimensional analysis.

# Usage

The source code for `MolPad` is stored on [Github](https://github.com/KaiyanM/MolPad). The app is hosted in the eponymous R package which can be downloaded and run on a local computer. We anticipate that some users may need more flexibility in their analyses, requiring backend R coding for tasks like setting up detailed operating models or downloading figure outputs. For such needs, the essential set of R functions employed in the Shiny app is accessible through the R package.

# Figures

![Dashboard Overview: `A`: cluster-level network, `B`: taxonomic-level bar plot, `C`:  a type-level line plot, and `D`: a feature-level table. \label{fig:dashboard}](dashboard.png)

![Example of discovering related patterns with network plot. For `a`, the two linked nodes are in the dashed box and have a closer inverse pattern than the other. For `b`, these groups are both less volatile on average and have similar inverse patterns.\label{fig:pattern}](pattern.png){ width=60% }

![Dashboard showing Groups 10, 7, 4, and 3 for the
bacterial(a.) and Group 4 for the eukaryotic(b.) community. Groups 10 and 4 have decreasing trends for both cheeses, and they all include largely Proteobacteria and Firmicutes. While Groups 3 and 7 have the opposite increasing trends, which include more Actinobacteria and Bacteroidetes. Among these, Groups 7 and 4 have the strongest periodicity, suggesting a more reproducible tendency for the corresponding main components. For the eukaryote community, most of the features followed the same stable pattern as in Group 4\label{fig:cheesecase}](cheesecase.png){ width=80% }


# References



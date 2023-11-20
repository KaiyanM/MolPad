---
title: 'MolPad: An R-Shiny Package for Cluster Co-Expression Analysis in Longitudinal Microbiomics'
tags:
  - R
  - Shiny
  - microbiomics
  - visualization
  - cluster analysis
  - network
authors:
  - name: Kaiyan Ma
    orcid: 0000-0002-7355-8924
    affiliation: 1
  - name: Kris Sankaran
    orcid: 0000-0002-9415-1971
    affiliation: "1, 2" 
  - name: Margaret Thairu
    orcid: 0000-0002-2799-6261
    affiliation: 2
affiliations:
 - name: University of Wisconsin-Madison, Department of Statistics, USA
   index: 1
 - name: Wisconsin Institute for Discovery, USA
   index: 2
date: 18 November 2023
bibliography: paper.bib

# Optional fields if submitting to a AAS journal too, see this blog post:
# https://blog.joss.theoj.org/2018/12/a-new-collaboration-with-aas-publishing
aas-doi: 
aas-journal: 
---

# Summary

The R-Shiny package MolPad provides an interactive dashboard for understanding the dynamics of longitudinal molecular co-expression in microbiomics. The main idea for addressing the issue is first to use a network to overview major patterns among their predictive relationships and then zoom into specific clusters of interest. It is designed with a focus-plus-context analysis strategy and automatically generates links to online curated annotations. The dashboard consists of a cluster-level network, a bar plot of taxonomic composition, a line plot of data modalities, and a table for each pathway, as illustrated in Fig \ref{fig:dashboard}. Further, the package includes functions that handle the data processing for creating the dashboard. This makes it beginner-friendly for users with less R programming experience. We illustrate these methods with a case study on a longitudinal, multi-platform metagenomics analysis for cheese communities.

# Statement of need

The realm of microbiomics is expanding rapidly, with numerous new studies and methodologies emerging [@BOKULICH20204048]. This highlights the need for visual exploration tools that can account for interaction across biological modalities [@6094057]. It’s also important to enable interpretations of dynamics and network structure because these have specific meanings in the genomic context [@corel:hal-01300043]. Another issue is the annotation of notable features. A characteristic of microbioem data is that each identical feature can be classified at several levels of taxonomic resolution and could have several IDs in different databases [@https://doi.org/10.1002/pro.3711]. Although relevant annotation is typically available online, it can be tedious to search through databases manually. Moreover, microbiome data often exhibit longitudinal variation. In this context, we must gain insight into the functioning of how individual features change and how they may influence related features. Thus, it depends upon analysis within one table and across tables. All of these have posed a challenge for unified visualization and interpretation. 

In response to the above issues, previous studies on interactive visualization tools have designed methods to work on such data. `microViz` [@microviz] provides a Shiny app for interactive exploration by pairing ordination plots and composition circular bar charts to show each taxon's prevalence and abundance. `GWENA` [@Lemoine_Scott-Boyer_Ambroise_Périn_Droit_2021] applies a network in conducting gene co‑expression analysis and extended module characterization in a single package to understand the underlying processes contributing to a disease or a phenotype. `NeVOmics` [@Zúñiga-León_Carrasco-Navarro_Fierro_2018] improved compatibility with a dynamic dashboard and facilitated the functional characterization of data from omics technologies. It also integrates over-representation analysis and network-based visualization to display enrichment results. These methods suggest the mechanisms that improve the utility of microbiomics visualization tools under analysis.

# Methods

## Network Generation
We first scale and cluster the trajectories across all molecular features to depict the longitudinal changes. For clustering, we use K-means and a built-in elbow method to choose the optimal number. Then, we predict a co-expression network for the extracted patterns, similar to GENIE3 [@GENIE3] creates gene regulatory networks. We also divide the prediction process into individual regression tasks. Each central pattern of a cluster is predicted from the expression patterns of all the other central patterns, using random forests. It is chosen because of its potential to model interacting features and non-linearity without strong assumptions. The Mean Decrease Accuracy of a subset of top predictors whose expression directly influences the expression of the target cluster is taken as an indication of a putative link. That is to say, based on the random forest prediction, if two groups of features are highly linked according to the network, they will have strongly related longitudinal patterns, as shown in Fig \ref{fig:pattern}.

## Network Navigation
Navigating the network in the MolPad dashboard follows three steps: First, choose a primary functional annotation. Adjustment options for fine-tuning include network layout and importance threshold for edge density. Bright green notes (Fig \ref{fig:dashboard}.A) represent clusters containing the most features in the chosen functional annotation. Second, brushing on the network reveals patterns of taxonomic composition (Fig \ref{fig:dashboard}.B) and typical trajectories  (Fig \ref{fig:dashboard}.C). The user can also zoom into specific taxonomic annotations by filtering. Third, they may view the feature table (Fig \ref{fig:dashboard}.D), examine the drop-down options for other related function annotations, and click the link for online details for the items of interest. The interface is designed to support iterative exploration, encouraging the use of several steps to answer specific questions, like comparing the distributional patterns between two functions or finding functionally important community members metabolizing a feature of interest. Overall, this aggregation adopted the focus-plus-context approach to address the low interoperability of the network graph, facilitating the examination of high-level details for individual features while providing contextual information about cluster interactions among microbiome data.

# Case Study: Cheese Data

Here we aim to highlight the versatility of the MolPad Dashboard with a case study of microbial communities on the wash-rind cheese' surface collected during cheese ripening [@doi:10.1128/msystems.00701-22]. It has multiple nested annotation labels ranging from kingdom to class, allowing flexible interpretation at multiple levels of resolution. 

Our goal is to verify conclusions from the original publication and provide an alternative visualization of the complex longitudinal measurements. According to the study, in the bacterial community, Firmicutes are dominant at initial timepoints and Proteobacteria quickly take over to dominate sample composition by the end of ripening. Further, cheeses Actinobacteria and Bacteroidetes were found to establish themselves in the final cheese A and C communities. To confirm these findings using the MolPad dashboard, we examined cheeses A and C across all three batches during weeks 2 to 13.

In applying the dashboard, we concatenated the time series for cheeses A and C. This allowed us to track unusual pattern combinations among different species and stages. We take the top four groups from the bacterial community for detailed analysis in Fig \ref{fig:cheesecase}. Overall, our results match the above research and could be used to provide intuitive explanations in supporting the findings, which substantiate the capabilities of `MolPad` as a reproducible tool to streamline the visualization of longitudinal patterns.

# Usage

The source code for `MolPad` is available on [Github](https://github.com/KaiyanM/MolPad). The app is hosted in the R package which can be downloaded and run locally. We anticipate that some users may need more flexibility in their analyses, requiring backend R development for tasks like setting up detailed operating models or downloading figure outputs. For such needs, the essential set of R functions employed in the Shiny app is accessible through the R package.

# Figures

![Dashboard Overview: `A`: cluster-level network, `B`: taxonomic-level bar plot, `C`:  a type-level line plot, and `D`: a feature-level table. \label{fig:dashboard}](dashboard.png)

![Example of discovering related patterns with network plot. The shade of edges stands for the vicinity of nodes. In the brushed area, Groups 1-7-8 (circled by solid black lines) and 1-2 (circled by blue dashed lines) are strongly linked. For Groups 1, 7, and 8, the patterns are w-shape with an evident peak at the same time section. For Groups 1 and 2, although Group 1 has higher volatility, they both show a highly overlapped increasing trend.\label{fig:pattern}](pattern.png){ width=110% }

![Dashboard showing Groups 10, 7, 4, and 3 for the bacterial (a.) and Group 4 for the eukaryotic (b.) community. Groups 10 and 4 have decreasing trends for both cheeses, and they all include largely Proteobacteria and Firmicutes. While Groups 3 and 7 have the opposite increasing trends, which include more Actinobacteria and Bacteroidetes. Among these, Groups 7 and 4 have the strongest periodicity, suggesting a more reproducible tendency for the corresponding main components. For the eukaryote community, most of the features followed the same stable pattern as in Group 4. \label{fig:cheesecase}](cheesecase.png){ width=80% }


# References



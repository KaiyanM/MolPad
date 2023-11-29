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
  - name: Margaret Thairu
    orcid: 0000-0002-2799-6261
    affiliation: 2
  - name: Kris Sankaran
    orcid: 0000-0002-9415-1971
    affiliation: "1, 2" 
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

Navigating the network in the MolPad dashboard follows three steps, as shown in Fig \ref{fig:flow}: First, choose a primary functional annotation. Adjustment options for fine-tuning include network layout and importance threshold for edge density. Bright green notes (Fig \ref{fig:dashboard}.A) represent clusters containing the most features in the chosen functional annotation. Second, brushing on the network reveals patterns of taxonomic composition (Fig \ref{fig:dashboard}.B) and typical trajectories  (Fig \ref{fig:dashboard}.C). The user can also zoom into specific taxonomic annotations by filtering. Third, they may view the feature table (Fig \ref{fig:dashboard}.D), examine the drop-down options for other related function annotations, and click the link for online details for the items of interest. The interface is designed to support iterative exploration, encouraging the use of several steps to answer specific questions, like comparing the distributional patterns between two functions or finding functionally important community members metabolizing a feature of interest. By applying a focus-plus-context approach, we can bridge the examination of high-level details related to individual features with contextual information about cluster interactions within the network visualization.

![Overview and workflow of using MolPad package. \label{fig:flow}](flow.png){ width=70% }


# Case Study: Cheese Data

Here we aim to highlight the versatility of the MolPad Dashboard with a case study of microbial communities on the wash-rind cheese' surface collected during cheese ripening. In the original research, [@doi:10.1128/msystems.00701-22] investigated the successional dynamics that occur within cheese rind microbial communities using a combination of 16S rRNA amplicon, Illumina, and PacBio sequencing. We functionally and taxonomically annotate (using eggNOG [@Huerta] and MMseqs2 [@Steinegger] the contigs they have generated from the Illumina reads, to demonstrate the utility of MolPad. Specifically, we focus on Cheese Sample A and Cheese Sample C. Overall, we are not only able to uncover similar findings as [@doi:10.1128/msystems.00701-22], with this subset, but we are also able to make new hypotheses, through the Dashboard. 

For example, when we filter for Actinomycetota (Actinobacteria)as the functional group, we see that there are no edges connecting to group 10 and group 3- the clusters that have the most features associated with Actinomycetoa for Cheese sample A (\ref{fig:cheesecase}.A). Looking at the pattern traces of these groups, (\ref{fig:cheesecase}.B), there is a peak in samples A4 (week 9) and A5 (week 13), which mirrors the 16S rRNA results of Saak et al. Since these two clusters do not have edges connecting them to other groups, this suggests that the Actinomycetoa features found in these groups follow a distinct longitudinal succession pattern that is independent. When looking at Actinomycetoa within Cheese Sample C we see a different pattern. Groups 2 and 5, have the most features associated with Actinomycetoa, but they are highly connected to the other groups (\ref{fig:cheesecase}.A). From these results, we can hypothesize that though Actinomycetoa features are more abundant in later time points for both cheese samples, their dynamics are differentially influenced. 
The authors found that Type VI secretion was enriched in Pseudomonadota bacteria (specifically, Psychrobacter), and hypothesized this enrichment was due to the importance of physical species interactions that occur with this habitat. Using the Dashboard, we searched for other secretion systems associated genes, to understand their dynamics within the community. Focusing on KEGG annotated Type IV secretion genes, we found that group 9 contained 13/12 of these genes. Within this group, features that cluster are ones that peak in Cheese sample C5 (week 13). This is also the most taxonomically diverse sample. From this, we can hypothesize that increased taxonomic diversity is also associated with increases in genes that are related to competitive species interactions. 


# Usage

The source code for `MolPad` is available on [Github](https://github.com/KaiyanM/MolPad). The app is hosted in the R package which can be downloaded and run locally. We anticipate that some users may need more flexibility in their analyses, requiring backend R development for tasks like setting up detailed operating models or downloading figure outputs. For such needs, the essential set of R functions employed in the Shiny app is accessible through the R package.

# Figures

![Dashboard Overview: `A`: cluster-level network, `B`: taxonomic-level bar plot, `C`:  a type-level line plot, and `D`: a feature-level table. \label{fig:dashboard}](dashboard.png)

![Example of discovering related patterns with network plot. The shade of edges stands for the vicinity of nodes. In the brushed area, Groups 1-7-8 (circled by solid black lines) and 1-2 (circled by blue dashed lines) are strongly linked. For Groups 1, 7, and 8, the patterns are w-shape with an evident peak at the same time section. For Groups 1 and 2, although Group 1 has higher volatility, they both show a highly overlapped increasing trend.\label{fig:pattern}](pattern.png){ width=110% }

![Dashboard showing Actinomycetota filtered network (A) with enrichment pattern for Cheese Sample-A (B) and Cheese Sample-C (C). Group 9 shows an enrichment of Type IV secretion genes. \label{fig:cheesecase}](cheesecase.png)

# Acknowledgments

Research reported in this publication was supported by the National Institute of General Medical Sciences of the National Institutes of Health under award number R01GM152744.

# References



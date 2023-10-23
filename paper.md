---
title: 'MolPad: Multi-Omics Longitudinal Pattern Dynamic Dashboard with Network'
tags:
  - R
  - multi-omics
  - visualization
  - dynamic dashboard
  - network
authors:
  - name: xxx
    orcid: xx
    equal-contrib: true
    affiliation: "1, 2" # (Multiple affiliations must be quoted)
  - name: Author Without ORCID
    equal-contrib: true # (This is how you can denote equal contributions between multiple authors)
    affiliation: 2
  - name: Author with no affiliation
    corresponding: true # (This is how to denote the corresponding author)
    affiliation: 3
  - given-names: Ludwig
    dropping-particle: van
    surname: Beethoven
    affiliation: 3
affiliations:
 - name: Lyman Spitzer, Jr. Fellow, Princeton University, USA
   index: 1
 - name: Institution Name, Country
   index: 2
 - name: Independent Researcher, Country
   index: 3
date: 13 August 2017
bibliography: paper.bib

# Optional fields if submitting to a AAS journal too, see this blog post:
# https://blog.joss.theoj.org/2018/12/a-new-collaboration-with-aas-publishing
aas-doi: 10.3847/xxxxx <- update this with the DOI from AAS once you know it.
aas-journal: Astrophysical Journal <- The name of the AAS journal.
---

# Introduction

In a longitudinal study, researchers are faced with the individuality of each feature that is repeatedly examined over a period of time. To characterize a feature, or to measure the similarity between features, remains a crucial issue. There are primarily two ways: “by what we see”: identifying patterns and trends from the data itself, or, “by what we know”:  using external annotation to boost the overall understanding. For recognizing patterns, machine learning does have an edge over humans, but no matter how good a model is, the final visualization can be a problem concerning existing static plots, especially for high-dimensional molecular data. A line plot, for example, is a faithful presentation of the whole-size data, thus people could hardly pick a visual focus from the tangle. Trimming down the feature size by variable selection and dimension reduction is a helpful step before doing visualization, but is still a palliative to the information burden. One endeavor taken by researchers is to invent charts that can carry more information and help people intuitively grasp complex data. Similarly, the other one is to build a dashboard and link several plots together to increase interaction capabilities. However, both of these plots or software often need more applicability. Another major issue is the annotation. Confronted with the volume feature size in exploratory research, humans eventually need to figure out how to cast light on each individual for interpretation. The special modality characteristic of multi-omics determines that each identical feature can be classified with various taxons and could have several IDs in different databases. Therefore, although the annotation is available online, it can be tedious to search for parts manually. Moreover, after characterization, we may further consider the features' interactions. Most present visualizations poorly evaluate longitudinal change across omics. In longitudinal data, we need to gain insight into the functioning of how individual features change and how they may influence related features. Thus, it depends upon analysis within one table and across tables. All of these have posed a challenge for unified visualization and interpretation. 


# Related Work

In response to the above issues, previous studies on multi-omics visualization tools have designed methods to work on complicated data. microViz\cite{microviz} provides a Shiny app for interactive exploration by pairing ordination plots and composition circular bar charts to show each taxon's prevalence and abundance. GWENA\cite{Lemoine_Scott-Boyer_Ambroise_Périn_Droit_2021} applies a network in conducting gene co‑expression analysis and extended module characterization in a single package to understand the underlying processes contributing to a disease or a phenotype. NeVOmics\cite{Zúñiga-León_Carrasco-Navarro_Fierro_2018} improved compatibility with a dynamic dashboard and facilitated the functional characterization of data from omics technologies. It also integrates Over-representation analysis methodology and network-based visualization to show the enrichment results. These methods suggest the mechanisms that improve the utility of multi-omics visualization tools under analysis.

# Methods

Our package provides a visualization dashboard tool for understanding the dynamics of molecular co-expression in microbiome multi-omics. The main idea for addressing the issue is to first use a cluster network to overview multi-omic relationships and then support interactivity to zoom into specific features of interest. We designed a focus-plu-context analysis strategy that links to online curated annotations. Specifically, we have access to a cluster-level network, a bar plot of taxonomic composition, a line plot of data modalities, and a table for each pathway, as illustrated in Figure \ref{fig:dashboard}. Besides, we have the processing functions with the whole pipeline for generating the dashboard wrapped up in the package, so it is also beginner-friendly for students with less R programming experience. 


\begin{figure}
\centering
\includegraphics[width=1\linewidth]{dashboard}

\caption{Dashboard Overview.}
A: cluster-level network, B: taxonomic-level bar plot, C:  a type-level line plot, D: a feature-level table. 

\label{fig:dashboard}

\end{figure}



\begin{figure}
\centering
\includegraphics[width=1\linewidth]{flow.png}
\caption{Workflow}
A pipeline across the operating procedures of the dashboard. 
\label{fig:flow}
\end{figure}




# Implementation

We will illustrate these methods with two case studies: discovering the omics change over time in soil samples collected from the fungus-growing ants' garden and a longitudinal, multi-platform meta-genomics analysis for cheese communities. 


# Data input

Our visualization pipeline starts with an optional pre-processing module with built-in functions. The raw input in our first case study includes three datasets collected from peptides, metabolites, and lipids generated using [??]. The package supports quantile normalization and KNN imputation to ensure library size effects and missing data are removed. The inputs are expected to be reformatted into a standard longitudinal data input format as in Table \ref{table:1}. One user-assigned type column will be taken as the category label to describe major groups in the data. It can be part of the annotation, as In the second case study, we used Kingdom as the type label column for cheese data. Note that the pre-processing is not a must, provided the matched format.

\begin{center}
\begin{tabular}{||c c c c c||} 
 \hline
 ID & Day 1 & Day 2 & ... & type \\ [0.5ex] 
 \hline\hline
 1 & 1.25 & 1.04 & ... & Peptide \\ 
 \hline
 2 & -2.33 & 0.22 & ... & Peptide  \\
 \hline
 3 & 0.25 & -0.52 &  ... & Metabolite  \\
 \hline
\end{tabular}
\captionof{table}{Standard longitudinal input format after pre-processing} 
\label{table:1}
\end{center}

Besides the data type we mentioned above, our methods allow three levels of information: functional annotation, taxonomy annotation, and feature annotation. These will be matched with ID as columns in the annotation data, which is another input for generating a dashboard. We support KeggID, GOID, and PFAM for automatic feature link generation, and the users should set the corresponding column name beforehand. 

# Network Construction

To depict the longitudinal changes, we first cluster trajectories across all molecular features and then reorganize the clusters into a network graph. As in Fig \ref{fig:dashboard} part A, here, we scaled all the time series to extract only the changing patterns and apply K-means for ordination. We use a built-in elbow method to choose the optimal number of clusters. Then, we take the centers of each group and run a random forest regression for each group centroid with all the other centroids as predictors. We pick the top five predictors to build a cluster network with the Mean Decrease Accuracy as the feature importance. Based on the random forest prediction, if two groups of features are highly linked according to the network, then they will have strongly related longitudinal patterns, as shown in Fig \ref{fig:pattern}.

\begin{figure}
\centering
\includegraphics[width=1\linewidth]{pattern.png}
\caption{Pattern}
Finding related patterns with the network plot. For .a, the two linked nodes are in the dashed box and have a closer inverse pattern than the other. For .b, these groups are both less volatile on average and have similar inverse patterns.
\label{fig:pattern}
\end{figure}


# Network Navigation




Navigating the network in the MolPad dashboard follows three steps as demonstrated in Fig \ref{fig:flow}: First, choose a primary functional annotation and adjust the edge density by tuning the threshold value on the importance score. Nodes that turnbright green (Fig \ref{fig:pattern}.A) represent clusters containing most features in the chosen functional annotation. Second, brushing on the network reveals patterns of taxonomic composition (Fig \ref{fig:pattern}.B) and typical trajectories  (Fig \ref{fig:pattern}.C). The user could also zoom into specific taxonomic annotations by filtering.
Third, view the feature table (Fig \ref{fig:pattern}.D) and examine the drop-down options for other related function annotations, and then click the link for online information on the interested items. The interface is designed to support iterative exploration, encouraging the use of several steps to answer specific questions, like comparing the pattern distribution between two functions or finding functionally important community members metabolizing a feature of interest. 



# Case Study
## Fungal garden

### Background
Fungal gardens serve as an external digestive system for the fungus-growing ant, with mutualistic fungi in the genus Leucoagaricus converting the plant substrate into energy.\cite{Francoeur_May_Thairu_Hoang_Panthofer_Bugni_Pupo_Clardy_Pinto-Tomás_Currie_2021} used a naturally evolved fungal garden consortium carrying out lignocellulose degradation that was gradually infected over time by a pathogenic fungus, Escovopsis, as a dynamic system to study, and analyzed the bacterial taxa present in this system to capture the community shifts and map the detected activity in space. \cite{}


### Problem
Since microbes can provide defense through competitively excluding pathogenic microbes\cite{Francoeur_May_Thairu_Hoang_Panthofer_Bugni_Pupo_Clardy_Pinto-Tomás_Currie_2021}, one question is to find the shifts in population compositions and metabolic potentials of a complex microbial consortium in response to perturbation. We studied (some pathway, name) with the MolPad dashboard and verified the (increasing/decreasing/u shape) pattern in (some feature).

The metaproteome data unveiled the studied samples were enriched with plant materials and a microbial community dominated by fungal and bacterial species. 

Leucogaricus was the main driver of lignocellulose degradation (a component of Carbohydrate metabolism). 

As the pathogenic fungus, Escovopsis, proliferated, the normalized spectra count of the native fungal species, Leucogaricus, were decreased and that of bacterial members were generally increased.  

Suggesting an active community response and potential interkingdom interactions under the impact of fungal infection. 
The community lipidome also indicated the shifts in microbial compositions and functions with significant trends (adjusted p-value < 0.05) by lipid class (i.e., phosphatic acids (PA), diacylglycerophosphocholines (PC), diacylglycerophosphoethanolamines (PE), and diacylglycerophosphoglycerol (PG), etc.) due to infection. 

Plant alpha-linolenic (18:3) containing lipids, which we previously found to be molecular indicators of lignocellulose degradation [1], were associated with native fungal community and decreased with the infection. 

Conversely, oleic acid (18:1) containing lipids (i.e., PA(18:1/18:1), PC(18:1/18:1), PE(18:1/18:1), and bacterial odd-chain fatty acids (i.e., PE(19:1/19:1); PG(19:1/19:1)) increased with infection. 

Metabolomic data captured the depletion of metabolites that are essential to fungal growth and infection such as myo-inositol. 

Phosphoric acid with antimicrobial activity against bacteria and fungi was one of the most abundant metabolites detected and significantly increased with the fungal infection, indicating potential interactions among bacteria, native and pathogenetic fungi.  



### Result
(screenshot)
The significant longitudinal patterns in (pathway name) are (explain). Compared with (taxa a), more (taxa b) are in the shape of (explain). These (taxa b) could affect (...) and lead to (...). If we check the KEGG ID, we will find (...). Thus, we detected signals of specific processes disappearing or becoming inactive.

## Cheese

### Background

In the process of producing cheese, regular washing with a brine solution is an aging practice that can homogenize the microbial communities on the cheese' surface and facilitate intermicrobial interactions. This study analyzed a longitudinal data set of three washed-rind cheese communities collected during cheese ripening. \cite{doi:10.1128/msystems.00701-22}

### Problem
The study revealed a highly reproducible microbial succession in each cheese. In the bacterial community, Firmicutes are dominant at the very beginning, and Proteobacteria quickly take over the domination by the end of ripening. Besides, Cheese A and C show a reproducible establishment of Actinobacteria and Bacteroidetes separately. To verify the above conclusions with the MolPad dashboard, we analyzed two cheeses(A and C) from all three batches in week 2~13. 

### Result
In applying the dashboard, we made an extended time series by connecting the last time point of cheese A with the first one of cheese C. This allowed us to track unusual pattern combinations among different species and stages. The bacterial community is larger and has a higher variety of patterns, so we take the top four for detailed analysis. Groups 10 and 4 have decreasing trends for both cheeses, and they all include largely Proteobacteria and Firmicutes. While Groups 3 and 7 have the opposite increasing trends, which include more Actinobacteria and Bacteroidetes. Among these, Groups 7 and 4 have the strongest periodicity, suggesting a more reproducible tendency for the corresponding main components. For the eukaryote community, most of the features followed the same stable pattern as in Group 4. Overall, our results match the above research and could be used to provide intuitive explanations in supporting the findings.


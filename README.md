# MolPad  <img src="https://github.com/KaiyanM/MolPad/blob/main/man/figures/logo.png" align="right" height="130" /></a>
Multi-Omics Longitudinal Pattern Dynamic Dashboard with Network

## Overview

MolPad offers a visualization dashboard tool designed to enhance our understanding of how molecular co-expression works in the context of multi-omics microbiome data. The approach involves using a cluster network to provide an initial overview of relationships across multiple omics, with the added functionality to interactively zoom in on specific areas of interest. To facilitate this analysis, we've developed a focus-plus-context strategy that seamlessly connects to online curated annotations.

Additionally, our package simplifies the entire pipeline for creating the dashboard. This user-friendly design makes it accessible even to students with limited R programming experience.


https://github.com/KaiyanM/MolPad/assets/108436174/eeb09056-9b1c-4a4b-8b5d-88cc8ac199c9

![screen recording](https://github.com/KaiyanM/MolPad/blob/main/man/figures/screen_recording.gif)

<img src="/man/figures/screen_recording.gif" width="250" height="250"/>

## Installation

```{r, eval = FALSE}
# Install the package in R:
install.packages("MolPad")
```

## Usage

### MolPad could help you with:  

1. Clutering the data with k-means and building a group network.
2. Find the significant trend patterns in your datasets.
3. Target the interaction between groups, taxons, and pathways.
4. Visualize the distribution of features in specific pathways on the group network.
5. Search for particular features and other user-defined labels.
6. Check detailed information on each feature through automatically generated hyperlinks.
7. Have a better overall understanding of the datasets.

### Workflow

<p align="center">
  <img src="man/figures/flow.png" width="450"/></a>  
</p>


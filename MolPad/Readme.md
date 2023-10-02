MolPad: Multi-Omics Longitudinal Pattern Dynamic Dashboard with Network
================
2023-05-31

## Background

This package provides a simple and powerful visualization dashboard for multi-omics researchers with less R programming experience to explore and analyze their data in different dimensions.

MolPad could help you with the following:  

1. Clutering the data with k-means and building a group network.
2. Find the significant trend patterns in your datasets.
3. Target the interaction between groups, taxons, and pathways.
4. Visualize the distribution of features in specific pathways on the group network.
5. Search for particular features and other user-defined labels.
6. Check detailed information on each feature through automatically generated hyperlinks.
7. Have a better overall understanding of the datasets.


## Dashboard

You could generate your dashboard easily, for example:

<img src="man/figures/dashboard.png" width="100%" />

## Workflow

<img src="man/figures/flow.png" width="100%" />

The first input is a list of datasets, where each should have been normalized and imputed. The second input is a pathway dataset. 

Note that for all the datasets, the first column must be `ID`. For more information, please check the corresponding functions.
# The network: method, limits, and what an edge supports

Reference for the network module. It explains how the edges of the dashboard are made
(`gNetwork()` in R, adapted from GENIE3), what is known about the method, and what a
statement about the network can and cannot claim. Sources are listed at the end.

## 1. What GENIE3 is

GENIE3 (Huynh-Thu, Irrthum, Wehenkel, Geurts, 2010) infers a gene regulatory network from
expression data.

- The problem of finding a network among p genes is split into p regression problems.
- In each one, the expression of one gene is predicted from the expression of all the other
  genes with a tree ensemble (random forest or extra-trees).
- The importance of a predictor gene in the model of a target gene is taken as the weight of
  a putative link "predictor -> target".
- All links of all p models are put in one list and ranked by weight. The output is this
  ranking, not a fixed network.
- It makes no assumption about the form of the relation (it can be non-linear and can involve
  several predictors together), and it gives directed links.
- It was the best performer in the DREAM4 In Silico Multifactorial challenge, and the method
  was again among the best in DREAM5.

## 2. How MolPad adapts it

Read from `R/gNetwork.R`:

| | GENIE3 | MolPad (`gNetwork`) |
|---|---|---|
| Nodes | genes | clusters of trajectories (k-means centres from `gClusters`) |
| Observations | samples or conditions, often hundreds | the time points (cheese: 9, from two cheeses) |
| Model | random forest or extra-trees per target | `randomForest` per cluster centre, all other centres as predictors |
| Weight | variance reduction summed over the trees | Mean Decrease Accuracy: % increase of the mean squared error when the predictor is permuted (`%IncMSE`) |
| Kept links | the full ranking | the `ntop` strongest predictors of each cluster (default 10; the cheese example uses 3) |
| Direction | predictor -> target | stored as `from` (target) and `var_names` (predictor); the page draws one undirected edge per pair, with the larger of the two weights |
| Threshold | left to the user | the "Importance Score" slider; default is the median weight, maximum the 75th percentile |

So an edge between two clusters on the page means: the mean course of one cluster was among
the best predictors of the mean course of the other, and the importance was above the slider.

## 3. Strengths

- No model form is assumed. Non-linear relations and relations that need several clusters
  together can be found, which a correlation network cannot do.
- It is simple and fast, and it scales to many nodes.
- Working on cluster centres instead of single features removes most of the noise of single
  features and keeps the number of models small.
- Each cluster gets its own model, so a cluster with a distinct course can still receive
  predictors.
- The result is a ranking, so the reader can move the threshold and see which links are
  stable (the slider does this).

## 4. Concerns

**From the method itself**

- An importance is not a test. GENIE3 gives a ranking without p-values, and its authors leave
  the choice of threshold open. There is no weight above which a link is "significant".
- The links are unsigned. An edge does not say whether the two courses move together or in
  opposite directions.
- Direction is weak. The two directions of a pair usually get similar weights, so the
  direction of a GENIE3 link should not be read as cause and effect. MolPad drops the
  direction on the page.
- Predictive does not mean causal. Two clusters driven by the same outside factor predict
  each other without acting on each other.
- Correlated predictors disturb the importance. Permutation importance in random forests is
  known to favour, or to share credit among, predictors that are correlated with each other
  (Strobl et al. 2008; Nicodemus et al. 2010). Cluster centres are often correlated or
  mirror images, so the credit for one relation can be split over several clusters or given
  to the wrong one.
- GENIE3 treats the observations as independent. It does not use the order of the time
  points; dynGENIE3 was written for time series for this reason.

**From the way MolPad uses it**

- Very few observations. Each forest is trained on one row per time point (9 for cheese) with
  about as many predictors. Importances from so little data are unstable.
- Not reproducible unless the seed is set. A random forest is random; running `gNetwork()`
  again can change weights and which links are kept.
- Sample groups are pooled. The time points of cheese A and cheese C are rows of one table,
  after each feature was scaled within each cheese. A link can come from a difference
  between the cheeses as well as from a shared course in time.
- `ntop` shapes the network. Every cluster keeps the same number of predictors, so the
  number of links per cluster before thresholding is set by `ntop`, not by the data. "Hub"
  and "isolated" depend on `ntop` and on the slider.
- `%IncMSE` can be zero or negative (permuting the predictor did not hurt). Such links are
  not evidence of a relation; the slider normally hides them.
- The weights of different target clusters are not on one scale. Each comes from its own
  model, and a cluster that is easy to predict gives larger importances.
- The clusters come first. Edges are between k-means centres, so they depend on the number
  of clusters and on the random start of k-means.
- With `method = "linear"` the weight is a regression coefficient, which is a different
  quantity (it has a sign and depends on scale); the notes above are about the random forest.

## 5. What the results can support

| Statement | Supported? |
|---|---|
| "The courses of cluster X and cluster Y are related: one helps to predict the other." | Yes. This is what an edge means. |
| "X and Y are more strongly linked than X and Z" (same target cluster) | Yes, as a ranking. |
| "This link remains at a high importance score, that one disappears." | Yes. It describes the ranking. |
| "X has many links", "X is isolated at this score" | As a description of the network at this `ntop` and this score, not as a property of the biology. |
| "X and Y have the same shape." | No. A link is not similarity: mirrored or shifted courses also predict each other. Compare the curves instead (ribbon module). |
| "X drives, regulates or causes Y." | No. The method shows prediction, and the page has no direction. |
| "The link is statistically significant." | No. There is no test behind the weight. |
| "The organisms or functions in X interact with those in Y." | Only as a hypothesis to test with other data. |
| "A weight of 4 here is stronger than a weight of 3 at another cluster." | Weak. Weights of different target clusters are not strictly comparable. |

## 6. How the agent should word it

- An edge means that the mean course of one cluster helps to predict that of the other. Say
  "linked", "connected", "their courses predict each other".
- Do not say that a cluster "regulates", "causes", "drives", "influences" or "interacts with"
  another, and do not call a link "significant": the weight is a ranking, not a test, and the
  page has no direction.
- A link does not mean that two curves look alike; mirrored or shifted courses are linked too.
- Give the importance score the answer was read at, because the edges change with it. "Hub"
  and "isolated" describe the network at that score, not the biology.
- Treat a link as a pointer to look at the two clusters (their patterns, their composition),
  not as the finding itself.

## Sources

- Huynh-Thu VA, Irrthum A, Wehenkel L, Geurts P (2010). Inferring regulatory networks from
  expression data using tree-based methods. PLoS ONE 5(9): e12776.
  https://pmc.ncbi.nlm.nih.gov/articles/PMC2946910
- Huynh-Thu VA, Geurts P (2018). dynGENIE3: dynamical GENIE3 for the inference of gene
  networks from time series expression data. Scientific Reports 8: 3384.
  https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5821733/
- Strobl C, Boulesteix AL, Kneib T, Augustin T, Zeileis A (2008). Conditional variable
  importance for random forests. BMC Bioinformatics 9: 307.
  https://www.ncbi.nlm.nih.gov/pmc/articles/PMC2491635/
- Nicodemus KK, Malley JD, Strobl C, Ziegler A (2010). The behaviour of random forest
  permutation-based variable importance measures under predictor correlation. BMC
  Bioinformatics 11: 110. https://link.springer.com/article/10.1186/1471-2105-11-110
- Huynh-Thu VA, Geurts P. Unsupervised gene network inference with decision trees and random
  forests (book chapter, with a section on improvements of GENIE3).
  https://orbi.uliege.be/bitstream/2268/230326/1/huynh-thu_tree_chapter_crossRef.pdf
- MolPad: `R/gNetwork.R`, `R/gClusters.R`, `R/d3_payload.R` (slider defaults), and the
  network section of the MolPad paper (2.2 Network Generation).

Sections 1 and 4 (first part) summarise the papers. Section 2, the second part of section 4
and sections 5 and 6 are read from the MolPad code and are our own assessment; they have not
been checked by experiments on MolPad data.

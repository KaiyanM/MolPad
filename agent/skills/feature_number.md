CARD feature_number: most features, most enriched, largest, dominant, top clusters.
kind=feature_number. Set top_n when the question gives a number ("which cluster" = 1, "the two
clusters" = 2); leave it empty for "the clusters that hold most of its features".
Examples
"Given Pseudomonadota, which cluster has the most features and what is its pattern?" -> feature_number top_n=1; pattern; needs_focus=true, network_area=false
"How do the two clusters most enriched for Pseudomonadota differ in class composition and shape?" -> feature_number top_n=2; level2, pattern; together
"For Pseudomonadota, what are the dominant temporal shapes among the clusters that carry most of its features?" -> feature_number; pattern; together
"For Bacteroidota, is there a single dominant pattern or are its features spread across many clusters?" -> feature_number; feature_number; needs_focus=false

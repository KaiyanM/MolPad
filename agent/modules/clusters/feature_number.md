CARD feature_number: most features, most enriched, largest, dominant, top clusters.
kind=feature_number. Set top_n when the question gives a number ("which cluster" = 1, "the two
clusters" = 2); leave it empty for "the clusters that hold most of its features".
Examples
"For <<EX_L1A>>, which cluster holds the most <<FEATURES>>, and what does its pattern look like?" -> feature_number top_n=1; pattern; needs_focus=true, network_area=false
"How do the two clusters most enriched for <<EX_L1A>> differ in <<L2>> mix and in shape?" -> feature_number top_n=2; level2, pattern; together
"For <<EX_L1A>>, what shapes do the clusters holding most of its <<FEATURES>> have?" -> feature_number; pattern; together
"For <<EX_L1B>>, is there one dominant cluster, or are its <<FEATURES>> spread over many?" -> feature_number; feature_number; needs_focus=false

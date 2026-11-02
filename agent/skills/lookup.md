CARD lookup: ids and the feature table (level 3).
kind=feature_lookup: where does this id / gene fall (the filters already hold the ids).
descriptor level3_column + level3_mode: "which contigs" (column ID, mode list), "most common KEGG" /
"GO terms recur" (mode frequency), "lack a GO annotation" / "have a GO annotation at all" (mode
coverage). An answer read from table rows needs no focus.
Examples
"Which cluster contains contig 10747, and what are its neighbours?" -> feature_lookup, then network neighbours; weight=neighbours
"Given Pseudomonadota and Gammaproteobacteria, which contigs carry KEGG ID K11901 and which cluster are they in?" -> feature_lookup; nothing; needs_focus=false (table rows)
"What molecular function does the most common KEGG ortholog in the Actinomycetota-enriched cluster have?" -> feature_number top_n=1; level3_column=KEGG_ID, level3_mode=frequency
"How many features in the selected clusters lack a GO annotation?" -> given; level3_column=GO_ID, level3_mode=coverage
"Which individual contigs in the most Actinomycetota-enriched cluster have KEGG annotations?" -> feature_number top_n=1; level3_column=KEGG_ID, level3_mode=list; needs_focus=false

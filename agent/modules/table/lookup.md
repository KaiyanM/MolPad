CARD lookup: ids and the feature table (level 3).
kind=feature_lookup: where does this id / gene fall (the filters already hold the ids).
descriptor level3_column + level3_mode: "which <<FEATURES>>" (column ID, mode list), "most common <<EX_IDKIND>>" / "<<EX_IDKIND2>> terms recur" (mode frequency), "lack a <<EX_IDKIND2>>
annotation" / "have a <<EX_IDKIND2>> annotation at all" (mode coverage). An answer read from table rows
needs no focus.
Examples
"Which cluster contains <<FEATURE>> <<EX_FID>>, and what are its neighbours?" -> feature_lookup, then network neighbours; weight=neighbours
"Within <<EX_L1A>> and <<EX_L2A>>, which <<FEATURES>> carry <<EX_ID>>, and in which cluster are they?" -> feature_lookup; nothing; needs_focus=false (table rows)
"What is the most common <<EX_IDKIND>> id in the cluster most enriched for <<EX_L1B>>?" -> feature_number top_n=1; level3_column=<<EX_IDCOL>>, level3_mode=frequency
"How many <<FEATURES>> of the selected clusters have no <<EX_IDKIND2>> annotation?" -> given; level3_column=<<EX_IDCOL2>>, level3_mode=coverage
"Which <<FEATURES>> of the cluster most enriched for <<EX_L1B>> have <<EX_IDKIND>> annotations?" -> feature_number top_n=1; level3_column=<<EX_IDCOL>>, level3_mode=list; needs_focus=false

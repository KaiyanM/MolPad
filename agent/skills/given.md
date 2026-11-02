CARD given: only when the user wrote cluster ids (put them in `clusters`) or says "the selected
clusters" (leave `clusters` empty). Never add it after another step.
Examples
"How many features in the selected clusters lack a GO annotation, and does this vary by cluster?" -> given; level3_column=GO_ID, level3_mode=coverage; needs_focus=false
"Which clusters follow the same curve as cluster 3?" -> given clusters=[3], then pattern compare tool=similar between=clusters

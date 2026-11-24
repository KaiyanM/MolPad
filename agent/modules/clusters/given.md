CARD given: only when the user wrote cluster ids (put them in `clusters`) or says "the selected
clusters" (leave `clusters` empty). Never add it after another step.
Examples
"How many <<FEATURES>> of the selected clusters have no <<EX_IDKIND>> annotation, and does that differ by cluster?" -> given; level3_column=<<EX_IDCOL>>, level3_mode=coverage; needs_focus=false
"Which clusters follow the same curve as cluster <<EX_CLN>>?" -> given clusters=[<<EX_CLN>>], then pattern compare tool=similar between=clusters

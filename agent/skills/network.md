CARD network: edge, connected, isolated, importance score, strongest, neighbours.
kind=network. criterion:
  most_edges | strongest_edge | isolated | connected_pairs (pairs still joined by an edge)
  neighbours (the clusters picked so far plus the clusters linked to them; also "similar shape to")
  connectivity (for the clusters picked so far: connected or isolated?)
threshold: 'max' / 'min' when the question moves the importance score, else leave empty.
descriptor weight: "what are its neighbours" (neighbours), edges per cluster (degree), "how many
connected components" (components).
Examples
"Which clusters have a similar shape to the cluster most enriched for Actinomycetota?" -> feature_number top_n=1, then network neighbours; pattern
"For Actinomycetota, are its most enriched clusters connected to the rest of the network or isolated?" -> feature_number, then network connectivity; network_area=true, one_by_one
"Which cluster pairs remain connected when the importance score is raised to its maximum?" -> network connected_pairs threshold=max; network_area=true, one_by_one
"At the lowest importance score, which clusters are still isolated?" -> network isolated threshold=min; network_area=true, one_by_one
"Which edge has the highest weight, and what are the two clusters' patterns?" -> network strongest_edge; pattern; network_area=true, together
"Which cluster has the most edges at the default importance score?" -> network most_edges; needs_focus=true, network_area=false
"How many connected components does the network have at the default score?" -> all; weight=components; needs_focus=false

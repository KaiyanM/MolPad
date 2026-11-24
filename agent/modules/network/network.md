CARD network: edge, connected, isolated, importance score, strongest, neighbours.
kind=network. criterion:
  most_edges | strongest_edge | isolated | connected_pairs (pairs still joined by an edge)
  neighbours (the clusters picked so far plus the clusters linked to them). "Similar shape" is not
  a network question: it compares curves (compare card).
  connectivity (for the clusters picked so far: are they linked to one another, or isolated?
  It needs a step before it that picks the clusters; never use it on all clusters.)
threshold: 'max' / 'min' when the question moves the importance score, else leave empty.
descriptor weight: "what are its neighbours" (neighbours), edges per cluster (degree), "how many
connected components" (components).
Examples
"For <<EX_L1B>>, are the clusters it is most enriched in linked to the rest of the network, or isolated?" -> feature_number, then network connectivity; network_area=true, together
"Which pairs of clusters are still linked at the highest importance score?" -> network connected_pairs threshold=max; network_area=true, one_by_one
"With the importance score at its lowest, which clusters have no edge at all?" -> network isolated threshold=min; network_area=true, one_by_one
"Which edge is the strongest, and what patterns do its two clusters have?" -> network strongest_edge; pattern; network_area=true, together
"Which cluster has the most edges at the default score?" -> network most_edges; needs_focus=true, network_area=false
"How many separate components does the network have at the default score?" -> all; weight=components; needs_focus=false

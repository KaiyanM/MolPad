TEMPLATES. Pick the one that fits the question and follow its steps; do not add steps it does not need.

TEMPLATE find, then relate (KIND multi_step): "which clusters are similar to / neighbours of the
cluster that <rule>?"
  1. Find the reference cluster by the rule, and read what the relation is about (its pattern for
     "similar shape", its edges for "neighbours").
  2. uses 1. Which other clusters relate to that cluster. Its conditions are only those that limit
     what is compared now (a sample group, "in cheese A"); the phylum that found the reference is
     not repeated, because it would filter the curves again.
Question: "Which clusters have a similar shape to the cluster that is most enriched for Actinomycetota?"
- "Which cluster holds the most Actinomycetota features, and what is its shape?" -> Actinomycetota:condition; feature_number; pattern
  reason: The reference cluster has to be found first; its curve is what the others are compared with.
- "Which other clusters have a similar shape to that cluster?" -> uses 1; given, pattern; pattern; curves
  reason: Every other cluster's curve is compared with the reference curve, per sample group.

TEMPLATE find, then check (KIND multi_step): "which clusters <rule>, and are they <property>?"
  1. Find the clusters by the rule.
  2. uses 1. Read the second property on those clusters (connected or isolated, their class mix,
     their annotations).
Question: "Which clusters peak late in cheese A, and are those clusters connected to each other?"
- "Which clusters peak late in cheese A?" -> A:condition; pattern
  reason: The late-peaking clusters are the ones the second half of the question is about.
- "Are those clusters connected to each other or isolated?" -> uses 1; given, network; weight
  reason: Edges between them would mean their curves predict each other.

TEMPLATE hypothesis (KIND evidence_chain): a claim that needs an argument.
  1. Locate the clusters the claim is about.
  2. Check that they stand for the group named (do they hold most of its features?).
  3. A contrast: the same reading for another group, or for the other sample group.
Each step picks its own clusters and repeats its conditions; `uses` stays empty.
Hypothesis: "Are the Actinomycetota features that peak late in cheese A following an independent succession?"
- "For Actinomycetota, which clusters peak late in cheese A?" -> Actinomycetota:condition, A:condition; pattern
  reason: First locate the late-peaking Actinomycetota features; without such clusters there is no succession to test.
- "For Actinomycetota, which clusters hold most of its features?" -> Actinomycetota:condition; feature_number
  reason: If most Actinomycetota features sit in the late-peaking clusters, the late peak describes the phylum and not a small subset.
- "For Bacillota, which clusters hold most of its features and what is their pattern in cheese A?" -> Bacillota:condition, A:condition; feature_number; pattern
  reason: A contrast phylum: if its main clusters are different or stay flat in cheese A, the Actinomycetota trajectory is its own.

CARD compare: two curves are set against each other (kind=pattern, criterion=compare).
- tool: opposite (the curves mirror each other: one up while the other is down)
        similar (same course) | shifted (same course, one later than the other)
        diverging (the gap between them grows) | converging (the gap shrinks)
- between: subjects (each cluster in one sample group against the same cluster in the other)
           windows (each cluster in one stretch of time against the same cluster in a later stretch)
           clusters (one cluster's curve against another cluster's; a first step may pick the
           cluster the others are compared with)
- a, b: the two curves, each with `subject` and, when the question names a stretch of time, the
  `start` and `end` timepoint columns. subjects: a and b hold the two sample groups. windows: a is
  the earlier stretch and b the later one of the same sample group; leave start and end empty for
  first half against second half. clusters: a holds the sample group and stretch the curves are
  read in, b stays empty; leave a empty to read every sample group.
- "similar shape to <a cluster picked before>" is tool=similar between=clusters after the step that
  picks that cluster (given, feature_number, ...). When the question names one sample group, set
  a.subject. When it reads several sample groups, set `match` only if the question says so: all
  ("in both cheeses") or any ("in either cheese"); otherwise leave it empty.
Examples
"Are there clusters whose cheese A and cheese C halves have opposite shapes?" -> pattern compare tool=opposite between=subjects a={subject: A} b={subject: C}
"Which clusters rise early in cheese A and then fall back?" -> pattern compare tool=opposite between=windows a={subject: A} b={subject: A}
"Do any clusters behave differently in A_1 to A_3 than in A_3 to A_5?" -> pattern compare tool=opposite between=windows a={subject: A, start: A_1, end: A_3} b={subject: A, start: A_3, end: A_5}
"Which pairs of clusters mirror each other in cheese C?" -> pattern compare tool=opposite between=clusters a={subject: C}
"Which clusters follow the same curve as cluster 3?" -> given clusters=[3], then pattern compare tool=similar between=clusters
"Which clusters have a similar shape to the cluster most enriched for Actinomycetota?" -> feature_number top_n=1, then pattern compare tool=similar between=clusters
"Which clusters follow the largest cluster's curve in either cheese?" -> feature_number top_n=1, then pattern compare tool=similar between=clusters match=any
"In which clusters do the two cheeses drift apart over ripening?" -> pattern compare tool=diverging between=subjects a={subject: A} b={subject: C}

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
  ("in both sample groups") or any ("in either sample group"); otherwise leave it empty.
Examples
"Is there a cluster whose <<EX_GA>> and <<EX_GB>> curves have opposite shapes?" -> pattern compare tool=opposite between=subjects a={subject: <<EX_GA>>} b={subject: <<EX_GB>>}
"Which clusters rise early in <<EX_GA>> and then fall back?" -> pattern compare tool=opposite between=windows a={subject: <<EX_GA>>} b={subject: <<EX_GA>>}
"Which clusters rise first and fall back later?" -> pattern compare tool=opposite between=windows
"Do any clusters behave differently from <<EX_T1>> to <<EX_T2>> than from <<EX_T2>> to <<EX_T3>>?" -> pattern compare tool=opposite between=windows a={start: <<EX_T1>>, end: <<EX_T2>>} b={start: <<EX_T2>>, end: <<EX_T3>>}
"Which pairs of clusters mirror each other in <<EX_GB>>?" -> pattern compare tool=opposite between=clusters a={subject: <<EX_GB>>}
"Which clusters follow the same curve as cluster <<EX_CLN>>?" -> given clusters=[<<EX_CLN>>], then pattern compare tool=similar between=clusters
"Which clusters have a shape like that of the cluster most enriched for <<EX_L1A>>?" -> feature_number top_n=1, then pattern compare tool=similar between=clusters
"Which clusters follow the largest cluster's curve in either sample group?" -> feature_number top_n=1, then pattern compare tool=similar between=clusters match=any
"In which clusters do <<EX_GA>> and <<EX_GB>> drift apart over time?" -> pattern compare tool=diverging between=subjects a={subject: <<EX_GA>>} b={subject: <<EX_GB>>}

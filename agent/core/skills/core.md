You plan the backend work for a data question about the dashboard. The question has already been
read: you get its roles (target rules, measures, comparison), the filters found in the data, and the
cards below for the rules that apply. Fill, for each (sub-)question in order:

steps (N4): the rule that picks the clusters. One step, or two steps when a second rule works on the
result of the first. Only the rule that picks clusters belongs here. What is then read from them
("... and what is its pattern", "which <<L2>> values make it up") is not a step. Use kind=all for "each
cluster", "rank the clusters", or a count over the whole network.
Kinds: <<KINDS>>.
The roles say which kind was read; follow them unless the question clearly says otherwise.

descriptor (N5): what is reported about the chosen clusters. Set every slot that applies. Do not
repeat what the selector already answers ("which clusters increase" needs no descriptor).
<<DESCRIPTOR>>

display (N6), once for the whole answer:
- needs_focus: does the user need to look at specific clusters to see the answer? false when the
  answer is a value for every cluster, one number about the whole network, a distribution or ranking
  over all clusters, or rows and counts read from the table. true otherwise.
- network_area: true when the importance slider must move to a stated position, or the targets only
  make sense as linked nodes (a cluster plus its neighbours, the two ends of the strongest edge,
  connected pairs, isolated nodes). false for one hub at the default score.
- grouping, when several clusters are in focus: together (they share one property or are contrasted,
  one message covers them) | one_by_one (separate groups such as "which increase, and which
  decrease", a vague criterion so several candidates are shown in turn, or one message per cluster).

Examples
"When does each cluster reach its maximum in <<EX_GA>>?" -> all; pattern; needs_focus=false
"How many <<FEATURES>> are in each cluster, and which cluster is the largest?" -> all; feature_number; needs_focus=false
"Order the clusters by their number of <<EX_L1B>> <<FEATURES>>." -> all; feature_number; needs_focus=false
"What share of the largest cluster is <<EX_L2A>>?" -> feature_number top_n=1; level2; needs_focus=true

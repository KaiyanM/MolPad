CARD pattern: the clusters are chosen by the shape of their curve.
kind=pattern. criterion:
  increase | decrease | increase_and_decrease (the question asks for both groups)
  peak_at (set `timepoint` for an exact column such as <<EX_T>>, else `position` early / mid / late)
  compare (two curves are set against each other; see the compare card)
  color_divergence (the colour mean lines disagree)
Set `subject` when the shape is read in one sample group.
Examples
"Which clusters rise steadily in <<EX_GA>>, and which fall?" -> pattern increase_and_decrease, subject=<<EX_GA>>; display one_by_one
"Which clusters rise steadily, and which fall?" -> pattern increase_and_decrease; display one_by_one
"Which clusters peak in the middle of the series, not at its start or end?" -> pattern peak_at position=mid; display together
"Which <<EX_IDKIND>> terms recur among the <<FEATURES>> of a cluster that peaks at <<EX_T>>?" -> pattern peak_at timepoint=<<EX_T>>
"Which clusters peak at <<EX_T>>?" -> pattern peak_at timepoint=<<EX_T>>
"In which cluster do the line colours disagree most?" -> pattern color_divergence; display one_by_one

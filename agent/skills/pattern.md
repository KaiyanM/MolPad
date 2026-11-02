CARD pattern: the clusters are chosen by the shape of their curve.
kind=pattern. criterion:
  increase | decrease | increase_and_decrease (the question asks for both groups)
  peak_at (set `timepoint` for an exact column such as C_5, else `position` early / mid / late)
  compare (two curves are set against each other; see the compare card)
  color_divergence (the colour mean lines disagree)
Set `subject` when the shape is read in one sample group.
Examples
"Which clusters increase steadily in cheese A, and which decrease?" -> pattern increase_and_decrease, subject=A; display one_by_one
"Which clusters peak in the middle of ripening rather than at the start or end?" -> pattern peak_at position=mid; display together
"Which GO terms recur among contigs in a cluster that peaks at C_5?" -> pattern peak_at timepoint=C_5
"In which cluster do the phyla (line colours) disagree most?" -> pattern color_divergence; display one_by_one

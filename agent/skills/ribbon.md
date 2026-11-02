CARD ribbon: the clusters are chosen by the ribbon of the pattern plot, the band between the highest
and lowest feature: tight / narrow / wide / spread out ribbon, "its features follow almost the same
trajectory", the ribbon widens or narrows.
kind=ribbon. criterion: tightest_ribbon | widest_ribbon | expanding_ribbon | contracting_ribbon
measure (tightest / widest only): mean_width | max_width | area when the question names one
("on average", "at any timepoint", "area"); leave it empty when it is vague: then each definition
gives its own answer. Leave top_n empty for a vague ribbon question, even after "which cluster".
Set `subject` when the ribbon is read in one sample group. A vague ribbon criterion shows several
candidates in turn: display one_by_one.
Examples
"Which cluster has the tightest ribbon, meaning its features follow almost the same trajectory?" -> ribbon tightest_ribbon; needs_focus=true, one_by_one
"Which cluster has the smallest ribbon area in cheese C?" -> ribbon tightest_ribbon measure=area subject=C
"Whose ribbon widens over ripening?" -> ribbon expanding_ribbon

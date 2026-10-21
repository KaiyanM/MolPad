"""Node cards of the decision tree as prompts.

Source: development/questions/cheese_decision_tree.md, section 3. The example
questions are from the cheese case study; the dataset block is built from the
data and config.py.
"""

import json


def dataset_block(ds, dash_state):
    cfg = ds.cfg
    level3 = "\n".join(f"  - {c}: {n}" for c, n in zip(cfg.level3, cfg.level3_notes))
    subjects = "; ".join(f"{s}: {', '.join(cols)}" for s, cols in ds.subjects.items())
    return f"""BACKGROUND
{cfg.background}

DATASET AND DASHBOARD
- Features are grouped into clusters {ds.clusters[0]} .. {ds.clusters[-1]}. Each cluster is one node of the network.
- Level 1 ({cfg.level1_name}), drop-down "Select a Functional Annotation". Values: {', '.join(ds.level1_values)}
- Level 2 ({cfg.level2_name}), multi-select "Select a Taxonomic Scope". Values per level 1:
  {json.dumps(ds.level2_by_level1)}
- Level 3, columns of the feature table:
{level3}
- Sample groups and their timepoint columns, in time order: {subjects}.
  Questions may speak of weeks; map them to the timepoint columns by position (first = early, last = late).
- The pattern plot shows one ribbon and mean line per cluster, coloured by {cfg.level1_name}.
- Network edges have a weight. An edge is drawn when weight > Importance Score.
  Importance Score now: {dash_state['min_weight']} (min {ds.slider_min}, max {ds.slider_max}).
- Clusters selected now: {', '.join(dash_state['selected_clusters'])}."""


KEYWORDS = """You pick the specific keywords out of a question about a dataset. They will be looked up
in the data afterwards, so copy each one as it is written in the question.

Pick
- names of categories at any level (for example a phylum or a class), including "unknown" when the
  question means the unknown category;
- ids (contig ids, KEGG ids such as K03196, GO ids such as GO:0005524);
- sample groups ("cheese A" -> "A") and timepoint names ("C_5");
- clusters named by the user ("cluster 3");
- named gene families, functions or other outside concepts ("Type IV secretion").

Do not pick generic words: cluster, pattern, feature, phylum, class, network, edge, importance
score, layout, "others", "the rest". Do not pick weeks, time spans or bare numbers ("week 6",
"timepoint 3", "the two clusters"). Return an empty list when the question names nothing specific.

Examples
"Given Pseudomonadota and Gammaproteobacteria, which contigs carry KEGG ID K11901?" -> Pseudomonadota, Gammaproteobacteria, K11901
"Which clusters increase steadily from week 2 to week 13 in cheese A, and which decrease?" -> A
"How many features with an unknown phylum fall into each cluster?" -> unknown
"Where do the Type IV secretion genes (KEGG) fall?" -> Type IV secretion
"Which cluster has the most edges at the default importance score?" -> (none)"""


def keyword_block(kmap_text):
    return ("KEYWORDS OF THIS QUESTION, looked up in the data without an LLM\n"
            "A keyword can only fill the slot of the level it was found in. A keyword that was not "
            "found is not a value of the data.\n" + kmap_text)


N0 = """You classify a question about an interactive dashboard. Decide what kind of question it is.

- out_of_scope: tells the agent to do a hand gesture whose result depends on screen position
  ("brush the top row", "drag nodes together"), or asks what a filter does to the display rather
  than to the data ("how many features disappear from the plot when ...").
- design: asks whether or how a dashboard control helps ("does switching to the circle layout make
  it easier ...", "what is the grid layout for"). Fill `control` and `value`.
- data: everything else. This is the normal case. A question is still a data question when it
  says "select", "restricting to" or "given": picking clusters or filters by a rule in the data
  (the strongest edge, a phylum, a class) is something the agent can do.

Examples
"Select only the clusters connected to the strongest edge: how do their shapes relate?" -> data
"Given Pseudomonadota and restricting to Gammaproteobacteria, does the dominant cluster change?" -> data
"Using the grid layout, brush the top row of nodes: what do those clusters have in common?" -> out_of_scope
"Drag the three most connected nodes together and brush them: do they share a dominant phylum?" -> out_of_scope
"Does switching to the circle layout make it easier to see which clusters form a connected component?" -> design, control=layout, value=circle
"Which cluster has the most edges at the default importance score?" -> data"""

N1 = """You check whether a data question about the dashboard can be run as written.

- ask: it refers to a cluster without saying which, and no rule in the question picks one
  ("for the same cluster, how does ..."). `note` = what to ask (a specific cluster, or an overview?).
- assume_default: it needs a threshold or setting that is not given (for example whether clusters are
  "connected" without an importance score). `note` = the assumed value, normally the current one.
- use_current_selection: it says "the selected clusters" or "these clusters". "Are there clusters
  whose ..." or "which clusters ..." searches all clusters by a rule and is ok.
- ok: nothing is missing. This is the normal case; choose it unless one of the three cases above
  clearly applies. Vague wording ("dominant", "most enriched", "similar shape", "tightest") is ok:
  the backend picks a metric. A named gene family, "a specific contig" or a hypothesis is ok. A rule such as "the largest cluster" or "the cluster that peaks at C_5" is
  enough to pick a cluster. A question that states the score ("at the default / maximum / lowest
  importance score") is ok.

Examples
"For the same cluster, how does the cheese C trajectory differ from the cheese A trajectory?" -> ask
"For Actinomycetota, are its most enriched clusters connected to the rest of the network or isolated?" -> assume_default
"How many features in the selected clusters lack a GO annotation?" -> use_current_selection
"Given Pseudomonadota, which cluster has the most features and what is its pattern?" -> ok
"Are there clusters whose cheese A and cheese C halves have opposite shapes?" -> ok"""

N2 = """You decide the reasoning shape of a data question about the dashboard.

- evidence_chain: a claim that needs an argument. "Is X associated with Y", "following an independent
  succession", any "why" or causal wording.
- direct: a lookup. Which / how many / what / rank / does X change / do they decline / do two
  things peak at different weeks / does it vary by cluster. This is the normal case: a yes-or-no
  question that one table of numbers settles is direct.

Examples
"For Bacillota, which clusters hold most of its features and do they decline over ripening?" -> direct
"Do Flavobacteriia and Bacilli peak at different weeks?" -> direct
"At which week does each cluster reach its maximum in cheese A, and is it the same week in cheese C?" -> direct
"Are the Actinomycetota features that peak late in cheese A following an independent succession?" -> evidence_chain
"Is the rise of secretion-system genes at C_5 associated with the higher taxonomic diversity of that sample?" -> evidence_chain
"Given Bacillota and class Bacilli versus Clostridia, do the two classes sit in the same clusters?" -> direct"""

N2_SPLIT = """A hypothesis about the data cannot be answered in one lookup. Split it into 2 to 4 sub-claims.
Each sub-claim must be a direct question that the dashboard data can answer by itself: it names its
own level-1 / level-2 / level-3 filter if it needs one, says how clusters are picked (by pattern, by
feature number, by network edges, or by looking up ids) and what is read from them. Do not refer to
"the clusters above"; repeat the condition instead. Order them as steps of the argument.

Example
Hypothesis: "Are the Actinomycetota features that peak late in cheese A following an independent succession?"
Sub-claims:
- "For Actinomycetota, which clusters peak late in cheese A?"
- "For Actinomycetota, which clusters hold most of its features and what is their pattern?"
- "For Bacillota, which clusters hold most of its features and what is their pattern?" """

N3 = """You fill the filter slots of a data question. Fill every slot that applies, leave the others empty.
Use only values listed in the dataset block.

- cols: the question is limited to one sample group ("in cheese A"). Do not set it when both groups
  are compared.
- level1: a level-1 value named as a condition, after "for", "given", "within", "enriched for".
- level2: a level-2 value named as a condition.
- level3_column + level3_values: specific ids (a contig ID, KEGG id, GO id).
  level3_has_annotation: the question is about rows that have any KEGG / GO annotation.
- external_concept: the question names a gene family or function instead of ids ("Type IV secretion
  genes"). Put the name here, and write the ids you know for it into level3_values
  (level3_column = the id column).
- contrast: two values are compared, so the filter is run twice.
  level1 / level2 = once per value of that slot.
  with_and_without_level2 = level 1 alone, then level 1 plus level 2 ("does it change when restricting to Y").

A taxon is not always a filter. In "what fraction of the largest cluster is Gammaproteobacteria" the
class is the thing being measured: filtering on it would change which cluster is largest. Set a
filter slot only when the taxon is a condition on the question. "Rank the clusters by number of X
features" does filter on X.

Examples
"Which clusters increase steadily in cheese A, and which decrease?" -> cols=A
"Which clusters have a similar shape to the cluster that is most enriched for Actinomycetota?" -> level1=[Actinomycetota]
"Given Pseudomonadota and restricting to Gammaproteobacteria, does the dominant cluster change?" -> level1=[Pseudomonadota], level2=[Gammaproteobacteria], contrast=with_and_without_level2
"Given Bacillota and class Bacilli versus Clostridia, do the two classes sit in the same clusters?" -> level1=[Bacillota], level2=[Bacilli, Clostridia], contrast=level2
"Do Flavobacteriia and Bacilli peak at different weeks?" -> level2=[Flavobacteriia, Bacilli], contrast=none
"Given Pseudomonadota and Gammaproteobacteria, which contigs carry KEGG ID K11901?" -> level1, level2, level3_column=KEGG_ID, level3_values=[K11901]
"Given Actinomycetota and Actinomycetes, how many contigs have a GO annotation at all?" -> level1, level2, level3_column=GO_ID, level3_has_annotation=true
"Where do the Type IV secretion genes (KEGG) fall?" -> external_concept="Type IV secretion", level3_column=KEGG_ID, level3_values=[K03196, K03197, ...]
"What fraction of the features in the largest cluster are Gammaproteobacteria?" -> all empty
"How many features with an unknown phylum fall into each cluster?" -> level2=[Unknown]"""

N4 = """You choose the rule that picks the clusters a data question is about. Give one step, or two
steps when a second rule works on the result of the first.

kind
- pattern: increase, decrease, peak, hump, opposite shape, tightest / widest ribbon. criterion:
    increase | decrease | increase_and_decrease (the question asks for both groups)
    peak_at (set `timepoint` for an exact column such as C_5, else `position` early / mid / late)
    compare (two curves are set against each other; see "compare" below)
    tightest_ribbon | widest_ribbon | color_divergence (the colour lines disagree)
  Set `subject` when the shape is read in one sample group.
- feature_number: most features, most enriched, largest, dominant, top clusters. Set top_n when the
  question gives a number ("which cluster" = 1, "the two clusters" = 2); leave it empty for "the
  clusters that hold most of its features".
- network: edge, connected, isolated, importance score, strongest, neighbours. criterion:
    most_edges | strongest_edge | isolated | connected_pairs (pairs still joined by an edge)
    neighbours (the clusters picked so far plus the clusters linked to them; also "similar shape to")
    connectivity (for the clusters picked so far: connected or isolated?)
  threshold: 'max' / 'min' when the question moves the importance score, else leave empty.
- feature_lookup: where does this id / gene fall (the filter slots already hold the ids).
- given: only when the user wrote cluster ids (put them in `clusters`) or says "the selected
  clusters". Never add it after another step.
- all: "each cluster", "rank the clusters", a count over the whole network; no selection needed.

compare: say which tool is used on which two curves.
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

Only the rule that picks clusters belongs here. What is then read from them ("... and what is its
pattern", "which classes make it up", "what are the two clusters' patterns") is not a selector step.

Examples
"Which clusters increase steadily in cheese A, and which decrease?" -> pattern increase_and_decrease, subject=A
"Which clusters peak in the middle of ripening rather than at the start or end?" -> pattern peak_at position=mid
"Which GO terms recur among contigs in a cluster that peaks at C_5?" -> pattern peak_at timepoint=C_5
"Which cluster has the tightest ribbon?" -> pattern tightest_ribbon
"Are there clusters whose cheese A and cheese C halves have opposite shapes?" -> pattern compare tool=opposite between=subjects a={subject: A} b={subject: C}
"Which clusters rise early in cheese A and then fall back?" -> pattern compare tool=opposite between=windows a={subject: A} b={subject: A}
"Do any clusters behave differently in A_1 to A_3 than in A_3 to A_5?" -> pattern compare tool=opposite between=windows a={subject: A, start: A_1, end: A_3} b={subject: A, start: A_3, end: A_5}
"Which pairs of clusters mirror each other in cheese C?" -> pattern compare tool=opposite between=clusters a={subject: C}
"Which clusters follow the same curve as cluster 3?" -> given clusters=[3], then pattern compare tool=similar between=clusters
"In which clusters do the two cheeses drift apart over ripening?" -> pattern compare tool=diverging between=subjects a={subject: A} b={subject: C}
"Given Pseudomonadota, which cluster has the most features and what is its pattern?" -> feature_number top_n=1
"Which clusters have a similar shape to the cluster most enriched for Actinomycetota?" -> feature_number top_n=1, then network neighbours
"Which cluster contains contig 10747, and what are its neighbours?" -> feature_lookup, then network neighbours
"For Actinomycetota, are its most enriched clusters connected to the rest of the network or isolated?" -> feature_number, then network connectivity
"Which cluster pairs remain connected when the importance score is raised to its maximum?" -> network connected_pairs threshold=max
"At the lowest importance score, which clusters are still isolated?" -> network isolated threshold=min
"Which edge has the highest weight, and what are the two clusters' patterns?" -> network strongest_edge
"How many features does each cluster contain, and which is the largest?" -> all
"How many connected components does the network have?" -> all
"Rank the clusters by number of Actinomycetota features." -> all"""

N5 = """You decide what a data question reports about the chosen clusters. Set every slot that applies.
Do not repeat what the selector already answers ("which clusters increase" needs no descriptor).

- pattern: "what is its pattern", "do they decline", "how do their shapes relate", "at which week
  does each cluster peak".
- level2: "which classes make up", "split", "fraction", "class composition", level-2 counts per cluster.
- level3_column + level3_mode: "which contigs" (column ID, mode list), "most common KEGG" / "GO terms
  recur" (mode frequency), "lack a GO annotation" / "have a GO annotation at all" (mode coverage).
- weight: "what are its neighbours" (neighbours), edges per cluster (degree), "how many connected
  components" (components).
- feature_number: "how many features does each cluster contain", "rank the clusters by number of ...",
  "is there a single dominant pattern or are its features spread across many clusters".

Examples
"Given Pseudomonadota, which cluster has the most features and what is its pattern?" -> pattern
"How do the two clusters most enriched for Pseudomonadota differ in class composition and shape?" -> level2, pattern
"What fraction of the features in the largest cluster are Gammaproteobacteria?" -> level2
"What molecular function does the most common KEGG ortholog in the Actinomycetota-enriched cluster have?" -> level3_column=KEGG_ID, level3_mode=frequency
"How many features in the selected clusters lack a GO annotation?" -> level3_column=GO_ID, level3_mode=coverage
"How many connected components does the network have at the default score?" -> weight=components
"Which clusters peak in the middle of ripening?" -> nothing
"Which cluster has the tightest ribbon?" -> nothing
"Which cluster has the most edges at the default importance score?" -> nothing
"Given Pseudomonadota and Gammaproteobacteria, which contigs carry KEGG ID K11901 and which cluster are they in?" -> nothing"""

N6 = """You decide how the dashboard should show the answer to a data question. You get the question,
the slots that were filled and the clusters the backend picked.

needs_focus (6a): does the user need to look at specific clusters to see the answer?
- false when the answer is a value for every cluster, a single number about the whole network, a
  distribution or ranking over all clusters, or rows and counts read from the table.
- true otherwise.

network_area (6b): true when the importance slider must move to a stated position, or the targets
only make sense as linked nodes (a cluster plus its neighbours, the two ends of the strongest edge,
connected pairs, isolated nodes). False for one hub at the default score: that is a single focus.

grouping (6c), when several clusters are in focus:
- together: the clusters share one property or are contrasted with each other, and one message
  covers them ("which clusters peak mid-ripening", "how do the two clusters differ").
- one_by_one: the answer has separate groups ("which increase, and which decrease"), or the
  criterion is vague so several candidates are shown in turn ("tightest ribbon", "disagree most"),
  or each cluster gets its own message (each isolated cluster, each pair).

Examples
"At which week does each cluster reach its maximum in cheese A?" -> needs_focus=false
"For Bacteroidota, is there a single dominant pattern or are its features spread across many clusters?" -> needs_focus=false
"Given Pseudomonadota and Gammaproteobacteria, which contigs carry KEGG ID K11901 and which cluster are they in?" -> needs_focus=false (table rows)
"Given Pseudomonadota, which cluster has the most features and what is its pattern?" -> needs_focus=true, network_area=false
"Which cluster has the most edges at the default importance score?" -> needs_focus=true, network_area=false
"Which edge has the highest weight, and what are the two clusters' patterns?" -> needs_focus=true, network_area=true, together
"Which cluster pairs remain connected when the importance score is raised to its maximum?" -> needs_focus=true, network_area=true, one_by_one
"For Pseudomonadota, what are the dominant temporal shapes among the clusters that carry most of its features?" -> needs_focus=true, network_area=false, together
"Which cluster has the tightest ribbon?" -> needs_focus=true, network_area=false, one_by_one"""

COMPOSE = """You write the messages an analysis agent prints next to an interactive dashboard.

You get the user's question, the backend data actions with their results, and a numbered list of
message slots. Each slot says where in the playback it appears and which clusters are in focus at
that moment. Write one message per slot, in order.

Rules
- Use only numbers, cluster ids and names that appear in the results. Never invent a value.
- Each message answers the part of the question its slot covers, and all of that part: if the
  question also asks for a pattern, a composition or a count, report it from the matching result
  (for a pattern, take shape, peak, ribbon width and constant features from the "text" the
  backend wrote per cluster and sample group; you may shorten it but not change it; say how
  several patterns compare). Keep it to 1-4 sentences.
- A slot's "report" list names descriptors that must appear in its message: pattern (from
  "evaluate pattern"), level2 (class counts or fractions), level3 (ids), weight (edges or
  neighbours), feature_number (counts per cluster). Leaving one out is an error.
- Name the metric when the backend chose one for a vague criterion.
- State every assumption listed under ASSUMPTIONS in the first message.
- If a result has an "error", or a filter left no features, say so plainly.
- If ids came from an external concept, say they come from model knowledge and were not looked up.
- A slot with a "write" instruction: follow it."""

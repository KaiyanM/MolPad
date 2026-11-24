"""Prompts of the pipeline (core/frame.py). No prompt names anything of a dataset: the words
(<<L1>>, <<FEATURE>> ...) come from the study, and the examples are written with values of the
loaded data (<<EX_...>>, see example_values). Both are filled in for_data, on every LLM call.

What the prompts say about the parts of the dashboard comes from the modules (agent/modules):
the selector kinds and measures with the words a question uses for them (<<...>> below), the
controls, what each view shows, and the lines about the data of each part.
"""

import re

from . import datacard
from .module import controls, explainable, hints, manifests, modules, named


def _with_modules(text):
    """Fill the <<...>> places of a prompt from the module manifests."""
    def lines(role):
        return "\n".join(f"- {k}" + (f": {v}" if v else "") for k, v in hints(role).items())
    return (text.replace("<<TARGETS>>", lines("target")).replace("<<MEASURE_HINTS>>", lines("measure"))
            .replace("<<KINDS>>", " | ".join(named("selectors")))
            .replace("<<PARTS>>", " | ".join(f"{n} (the {t.lower()})" for n, t in explainable().items()))
            .replace("<<MEASURES>>", " | ".join(named("measures"))))


def for_data(text, ds=None):
    """Fill the places of a prompt, card or manifest text that name things of the dataset:
    <<L1>> and <<L2>> (what the two levels are called), <<FEATURE>> (one row), <<IDS>> (the ids
    with an example each) and <<ID_COLUMNS>> (how an id column is named in words). Without a
    dataset the generic words are used. Every LLM call goes through this (llm.ask)."""
    if "<<" not in text:
        return text
    text = text.replace("<<FEATURES>>", "<<FEATURE>>s") if ds is None else text
    if ds is None:
        words = {"L1": "level-1 value", "L2": "level-2 value", "FEATURE": "feature", "FEATURES": "features",
                 "IDS": "feature ids, database ids", "ID_COLUMNS": '"KEGG annotations"'}
    else:
        card = ds.card
        feature = card["feature"]["name"]
        kinds = [i.get("type") or c for c, i in card["ids"].items()]
        words = {"L1": card["level1"]["name"], "L2": card["level2"]["name"], "FEATURE": feature,
                 "FEATURES": feature + "s",
                 "IDS": ", ".join([f"{feature} ids"] + [datacard.id_note(card, c) for c in card["ids"]]),
                 "ID_COLUMNS": ", ".join(f'"{k} annotations"' for k in kinds) or '"annotations"'}
    for key, word in words.items():
        text = text.replace(f"<<{key}>>", word)
    return _with_examples(text, ds)


# The words examples are written with, when the loaded data has nothing to put there.
_EXAMPLE_FALLBACK = {"L1A": "X", "L1B": "Y", "L2A": "P", "L2B": "Q", "L2C": "R", "GA": "A", "GB": "B",
                     "T": "T3", "T1": "T1", "T2": "T2", "T3": "T3", "ID": "ID123", "IDKIND": "id",
                     "IDCOL": "ID", "IDKIND2": "id", "IDCOL2": "ID", "FID": "1", "CL": "cluster 3", "CLN": "3"}


def example_values(ds):
    """Values of the loaded data that the examples are written with, {key: value}. A key is left
    out when the data has nothing for it (one sample group only, no id column ...).

    L1A, L1B   the two level-1 values with the most features
    L2A, L2B   the two level-2 values with the most features under L1A;  L2C  the first under L1B
    GA, GB     two sample groups;  T1, T2, T3  first, middle and last timepoint of GA;  T  the last
               timepoint of the last group
    ID, IDKIND, IDCOL   an id of the first id column, its kind ("KEGG") and its column;
    IDKIND2, IDCOL2     the same for the second id column (else the first again)
    FID        the id of a feature;  CL, CLN  a cluster and its number
    """
    if getattr(ds, "_example_values", None) is not None:
        return ds._example_values
    cfg, card, f = ds.cfg, ds.card, ds.features
    known = f[~f[cfg.level1].isin(datacard.PLACEHOLDERS) & ~f[cfg.level2].isin(datacard.PLACEHOLDERS)]
    out = {}
    l1 = list(known[cfg.level1].value_counts().index)
    for key, value in zip(("L1A", "L1B"), l1):
        out[key] = value
    under = lambda v: list(known[known[cfg.level1] == v][cfg.level2].value_counts().index)
    if l1:
        l2 = under(l1[0]) + [v for v in known[cfg.level2].value_counts().index if v not in under(l1[0])]
        for key, value in zip(("L2A", "L2B"), l2):
            out[key] = value
        other = [v for v in (under(l1[1]) if len(l1) > 1 else l2) if v not in (out.get("L2A"),)]
        if other:
            out["L2C"] = other[0]
    groups = [s for s, cols in ds.subjects.items() if cols]
    if len(groups) > 1:
        out["GA"], out["GB"] = groups[0], groups[1]
    cols = ds.subjects[groups[0]] if groups else list(ds.timepoints)
    if cols:
        out["T1"], out["T2"], out["T3"] = cols[0], cols[len(cols) // 2], cols[-1]
        out["T"] = (ds.subjects[groups[-1]] if groups else cols)[-1]
    ids = [(c, i) for c, i in card["ids"].items() if i.get("example")]
    for n, (col, i) in enumerate((ids + ids[:1])[:2]):
        kind = i.get("type") or col
        if n == 0:
            out["ID"], out["IDKIND"], out["IDCOL"] = i["example"], kind, col
        else:
            out["IDKIND2"], out["IDCOL2"] = kind, col
    if len(f):
        out["FID"] = str(f[cfg.id_col].iloc[0])
    if ds.clusters:
        cl = ds.clusters[min(2, len(ds.clusters) - 1)]
        out["CL"], out["CLN"] = cl, str(ds.cluster_number(cl))
    ds._example_values = {k: str(v) for k, v in out.items()}
    return ds._example_values


def _with_examples(text, ds):
    """Fill the <<EX_...>> places with values of the loaded data, so that every example names
    things that exist in it. An example line (a line that starts with a quoted question) that
    needs something the data does not have is left out; elsewhere a neutral word is used."""
    if "<<EX_" not in text:
        return text
    have = example_values(ds) if ds is not None else {}
    lines = []
    for line in text.split("\n"):
        keys = set(re.findall(r"<<EX_([A-Z0-9]+)>>", line))
        if keys - set(have) and line.lstrip().startswith('"') and ds is not None:
            continue
        for key in keys:
            line = line.replace(f"<<EX_{key}>>", have.get(key, _EXAMPLE_FALLBACK[key]))
        lines.append(line)
    return "\n".join(lines)


def data_block(ds):
    """What the data is, in two or three lines, for a writer that gets no value lists."""
    card = ds.card
    return "\n".join([card["background"],
                      f"One feature is a {card['feature']['name']}. Level 1 is the "
                      f"{datacard.level_note(card, 'level1')}. Level 2 is the {datacard.level_note(card, 'level2')}."])


def views_block():
    """What each view of the page shows, one line each, and what links them."""
    views = [m for m in manifests() if m.kind == "view"]
    return "\n".join(["THE DASHBOARD"] + [f"- {m.title}: {m.about}" for m in views] + [
        "- The views are linked: the filters apply to every view, and the bar, the ribbon plot and the "
        "table show the clusters selected on the network."])



COMPOSE = """You write the messages an analysis agent prints next to an interactive dashboard.

You get the user's question, the findings of the backend data actions (short lines, each data
action with an id such as [d2]), and a numbered list of message slots. Each slot says where in the
playback it appears, which clusters are in focus at that moment, and which findings it rests on.
Write one message per slot and give each text the number of its slot. Never merge two slots.

The user sees every number behind a message in an Evidence dropdown under it. So a message gives
the conclusion, not the data.

Rules
- Answer the part of the question the slot covers directly, in 1-3 sentences. State the conclusion
  and at most the one number that decides it (the winning value, or the margin when it is small).
- Do not list values per cluster, per timepoint or per <<L2>>; do not repeat the findings line by line.
- Use only cluster ids, names and numbers that appear in the findings. Never invent a value.
- A slot's "report" list names descriptors the message must cover: pattern (shape and peak, from
  "evaluate pattern"), level2 (the dominant <<L2>> values), level3 (the ids), weight (edges or
  neighbours), feature_number (how many features). Cover each in a few words; leaving one out is
  an error. When several patterns are reported, say how they compare.
- Name the metric in a few words when the backend chose one for a vague criterion. When several
  definitions were tried (e.g. ribbon mean width, max width, area), name the definition this
  message is about and say whether the definitions agree.
- State every assumption listed under ASSUMPTIONS in the message of slot 1, and only there. Notes
  about words that are not data values are not assumptions: leave them out.
- If a finding says "failed", or a filter left no features, say so plainly.
- If ids came from model knowledge (a finding says "from model knowledge, not looked up"), the
  answer is about the features that carry those ids, not about the named function or family as a
  fact: write "the features with these ids", say once that the list comes from memory and should
  be checked, and do not repeat the ids (the step shows them).
- A slot with clusters in focus opens with exactly one sentence saying why they are shown. Take
  the reason from the slot's own "why" field and say it in plain words; never give a reason the
  "why" field does not state. When "why" says a cluster is the example of a value, add its share
  from the findings. Then answer for those clusters. At most 3 sentences.
- Name a <<L2>> for a cluster only when a finding states that cluster's <<L2>> mix or example
  reason. Never infer a cluster's <<L2>> from the question.
- A filter keeps only the values it names. Never conclude from a filtered run that a cluster
  "contains only" that <<L2>> or "does not include" another one: give the counts from the
  "evaluate level2" finding instead, and give <<L2>> mix as counts, not percentages.
- When a finding compares the clusters picked for each value ("compare clusters between ..."),
  answer from it: which clusters are shared and which belong to one value only.
- A slot with several clusters in focus: they were picked together for one reason. Give that
  shared reason once, then say what the clusters have in common and where they differ. Do not
  write one sentence per cluster.
- A slot with "seen_before": an earlier message already introduced these clusters. Do not repeat
  why they were picked or what was said about them; say only what this step adds.
- A slot's "purpose" says what its step of the argument tests. Say what the result means for that
  purpose, in a few words, without repeating the purpose itself.
- A reason must agree with the findings. If "why" says a cluster was picked for something the
  pattern finding does not show (picked as a late peak, but the pattern is flat), say so.
- A slot with a "write" instruction: follow it."""


PARSE = """You read a question about an interactive dashboard and fill its roles. Code looks every
mention up in the data afterwards, so copy mentions exactly as written. You decide the roles only;
the data values are listed below so you can tell a data name from a generic word.

K: kind
- out_of_scope: tells the agent to do a hand gesture whose result depends on screen position
  ("brush the top row", "drag nodes together"), or asks what a filter does to the display rather
  than to the data ("how many features disappear from the plot when ...").
- design: asks whether or how a dashboard control helps ("does switching to the circle layout make
  it easier ...", "what is the grid layout for"). Fill `control` and `value`.
- method: asks how a part of the dashboard is made, or what its results mean or can prove, not what
  the data shows ("how is the network built", "what does an edge mean", "does a link mean one
  cluster causes the other", "is this link significant", "how were the clusters made", "why k-means").
  Fill `part`: <<PARTS>>. A question that asks for a result is data ("which clusters are linked"),
  also when it asks what the result means in the same breath ("which edge is the strongest, and does
  that mean one cluster drives the other"): the answer then explains the result it shows.
- data: everything else. This is the normal case. "Select", "restricting to" or "given" with a rule
  in the data (the strongest edge, a <<L1>>, a <<L2>>) is still data: the agent can do that.
For out_of_scope, design and method, leave the other roles empty.

R: status (data only)
- ask: refers to a cluster without saying which, and no rule picks one ("for the same cluster ...").
  `note` = what to ask (a specific cluster, or an overview?).
- assume_default: needs a setting that is not given (whether clusters are "connected" without an
  importance score). `note` = the assumed value, normally the current one.
- use_current_selection: "the selected clusters", "these clusters".
- ok: the normal case. Vague wording ("dominant", "most enriched", "similar shape", "tightest"),
  a named gene family, "a specific <<FEATURE>>", a hypothesis, or a rule such as "the largest cluster"
  are ok. "Which clusters ..." searches all clusters and is ok.

H: shape (data only)
- evidence_chain: a claim that needs an argument: "is X associated with Y", "following an independent
  succession", any "why" or causal wording.
- multi_step: asks which OTHER clusters relate to a cluster that a rule has to find first ("similar
  shape to the cluster most enriched for X", "the neighbours of the largest cluster"), or asks a
  second thing about clusters the first half picks ("which clusters ..., and are those connected?").
  Picking clusters by one rule and reading something from them ("the pattern of the largest
  cluster", "are its most enriched clusters connected or isolated") is direct, not multi_step.
- direct: a lookup (which / how many / what / rank / does X change / do two things peak at different
  time points). The normal case: a yes-or-no question that one table of numbers settles is direct.

mentions: the specific terms that may name something in the data, each with its role.
- Pick names of categories at any level (a <<L1>>, a <<L2>>, "unknown" when it means the unknown
  category), ids (<<IDS>>), annotation columns named without ids
  (<<ID_COLUMNS>>), sample groups by their name, also inside other words ("sample <<EX_GA>>" ->
  "<<EX_GA>>"), timepoint names ("<<EX_T>>"), clusters named by the user ("cluster <<EX_CLN>>").
- Do not pick generic words (cluster, pattern, feature, <<L1>>, <<L2>>, network, edge, importance
  score, layout, "others"), time words (week, day), time spans or bare numbers.
- role: condition = limits the data the question is asked about (C: "for X", "given X", "within",
  "in <<EX_GA>>", "<<FEATURES>> that carry <<EX_ID>>"); compare = one side of a comparison (D: "X versus Y",
  "is it the same in <<EX_GB>>"); measure = the thing read or counted on the clusters (B: "what
  fraction are <<EX_L2A>>", "which have <<EX_IDKIND>> annotations"); target = names the clusters (A:
  "cluster <<EX_CLN>>", "the cluster that peaks at <<EX_T>>").
  A category name is not always a condition: in "what fraction of the largest cluster is <<EX_L2A>>"
  it is measured; filtering on it would change which cluster is largest. "Rank the clusters by number
  of X features" does limit the data to X: condition.

target (A, then E): the rule(s) that pick clusters, in order:
<<TARGETS>>
measure (B): what is read from the picked clusters:
<<MEASURE_HINTS>>
compare (D): level1 / level2 (two values of that level, filter run once per value) |
with_and_without_level2 ("does it change when restricting to Y") | curves (two curves: sample groups,
time windows or clusters) | none.
outside_concept + outside_ids: a function or family named in words instead of ids; write every id of
it that you know, not an example or two.

Examples (K/R/H; mentions as text:role; target; measure; compare)
"For <<EX_L1A>>, which cluster holds the most <<FEATURES>>, and what does its pattern look like?" -> data/ok/direct; <<EX_L1A>>:condition; feature_number; pattern
"Within <<EX_L1A>>, does the largest cluster stay the same when only <<EX_L2A>> is kept?" -> data/ok/direct; <<EX_L1A>>:condition, <<EX_L2A>>:compare; feature_number; -; with_and_without_level2
"Within <<EX_L1A>>, <<EX_L2A>> versus <<EX_L2B>>: are the two found in the same clusters?" -> data/ok/direct; <<EX_L1A>>:condition, <<EX_L2A>>:compare, <<EX_L2B>>:compare; feature_number; -; level2
"Do <<EX_L2A>> and <<EX_L2C>> peak at different time points?" -> data/ok/direct; <<EX_L2A>>:condition, <<EX_L2C>>:condition; example; pattern
"What share of the largest cluster is <<EX_L2A>>?" -> data/ok/direct; <<EX_L2A>>:measure; feature_number; level2
"Which clusters rise steadily in <<EX_GA>>, and which fall?" -> data/ok/direct; <<EX_GA>>:condition; pattern
"Is there a cluster whose <<EX_GA>> and <<EX_GB>> curves have opposite shapes?" -> data/ok/direct; <<EX_GA>>:compare, <<EX_GB>>:compare; pattern; -; curves
"When does each cluster reach its maximum in <<EX_GA>>, and is that the same time point in <<EX_GB>>?" -> data/ok/direct; <<EX_GA>>:compare, <<EX_GB>>:compare; all; pattern
"Which clusters have a shape like that of the cluster most enriched for <<EX_L1B>>?" -> data/ok/multi_step; <<EX_L1B>>:condition; feature_number, pattern; pattern; curves
"Within <<EX_L1A>> and <<EX_L2A>>, which <<FEATURES>> carry <<EX_ID>>?" -> data/ok/direct; <<EX_L1A>>:condition, <<EX_L2A>>:condition, <<EX_ID>>:condition; feature_lookup
"Within <<EX_L1B>>, how many <<FEATURES>> have a <<EX_IDKIND>> annotation at all?" -> data/ok/direct; <<EX_L1B>>:condition, <<EX_IDKIND>> annotation:condition; feature_number; level3
"Which <<FEATURES>> of the cluster most enriched for <<EX_L1B>> have <<EX_IDKIND>> annotations?" -> data/ok/direct; <<EX_L1B>>:condition, <<EX_IDKIND>> annotations:measure; feature_number; level3
"Where do the <<FEATURES>> of <a function or family named in words> fall (<<EX_IDKIND>>)?" -> data/ok/direct; feature_lookup; outside_concept=<the name as written>, outside_ids=[every <<EX_IDKIND>> id of it that you know, not only one or two]
"Which <<EX_IDKIND>> terms recur among the <<FEATURES>> of a cluster that peaks at <<EX_T>>?" -> data/ok/direct; <<EX_T>>:target; pattern; level3
"Which cluster has the narrowest ribbon?" -> data/ok/direct; ribbon
"Which pairs of clusters are still linked at the highest importance score?" -> data/ok/direct; network
"How many separate components does the network have at the default score?" -> data/ok/direct; all; weight
"For <<EX_L1B>>, are the clusters it is most enriched in linked to the rest of the network, or isolated?" -> data/assume_default/direct; <<EX_L1B>>:condition; feature_number, network
"How many <<FEATURES>> of the selected clusters have no <<EX_IDKIND>> annotation?" -> data/use_current_selection/direct; <<EX_IDKIND>> annotation:measure; given; level3
"For the same cluster, how does the <<EX_GB>> curve differ from the <<EX_GA>> curve?" -> data/ask/direct
"Is the rise of <<EX_L1A>> <<FEATURES>> at <<EX_T>> linked to the mix of <<L2>> values in that sample?" -> data/ok/evidence_chain
"Does the circle layout make it easier to see which clusters form one component?" -> design, control=layout, value=circle
"If two clusters are linked, does one of them cause the other to change?" -> method, part=network
"How were the features put into clusters?" -> method, part=clusters
"In the grid layout, brush the top row of nodes: what do they share?" -> out_of_scope"""

BREAKDOWN = """The question cannot be answered in one lookup. Split it into 2 to 4 direct sub-questions,
in the order they have to be answered. KIND says what the split is for:
- multi_step: the question needs the answer of one lookup before it can ask the next ("similar to the
  cluster that ..."). The sub-questions are the steps that find the answer.
- evidence_chain: a hypothesis. The sub-questions, together, argue for or against it; prefer the
  angles the data can actually test.

Each sub-question must be answerable from the dashboard data: it says how clusters are picked (by
pattern, ribbon, feature number, network edges, looking up ids) and what is read from them.
- A sub-question that picks its own clusters names its own conditions (level 1 / level 2 / level 3
  values, sample group). Do not refer to "the clusters above"; repeat the condition.
- A sub-question that continues with the clusters an earlier one found sets `uses` to the number of
  that sub-question (1 for the first) and calls them "that cluster" or "those clusters". Its target
  starts with `given`.

"The common / typical / main patterns of X" means the patterns of the clusters that hold most of X:
that is one sub-question (target feature_number, measure pattern), not one for the patterns and
another for the sizes. "Similar shape" is only for a comparison with a cluster named or found before.

Every sub-question must add something new. Do not ask twice for the same clusters picked the same
way, and do not repeat an earlier sub-question with one more condition. Give each sub-question a
`reason`: one sentence for the user that says why this step comes here and, for a hypothesis, what
result would support or weaken it. The reason is shown in the chat before the step.

For each sub-question fill its roles the way they are described below: mentions (text copied from
the sub-question, role condition / compare / measure / target), target, measure, compare,
outside_concept and outside_ids. Use only data values listed below in mentions, written as the data
names them: a sample group by its name ("sample <<EX_GA>>" -> "<<EX_GA>>"), not by the words of the
question. A sample group the curves are read in is a condition when there is one ("in <<EX_GA>>") and
a compare when there are several ("in either sample group" -> <<EX_GA>>:compare, <<EX_GB>>:compare).

Roles
- target: <<KINDS>>
  ("similar shape to" is pattern with compare = curves; network is for edges and neighbours)
- measure: <<MEASURES>>
- compare: none | level1 | level2 | with_and_without_level2 | curves"""


def parse_context(ds):
    """What parse needs: names of things, not settings. No importance score, no selection."""
    cfg, card = ds.cfg, ds.card
    level3 = "; ".join(f"{c} ({n})" for c, n in zip(cfg.level3, cfg.level3_notes))
    subjects = "; ".join(f"{datacard.group_note(card, s)}: {', '.join(cols)}" for s, cols in ds.subjects.items())
    said = " ".join(t for t in (datacard.groups_sentence(card), datacard.time_note(card)) if t)
    return f"""BACKGROUND
{cfg.background}

DATA NAMES
- One feature is a {card['feature']['name']}.
- Level 1 ({datacard.level_note(card, 'level1')}): {', '.join(ds.level1_values)}
- Level 2 ({datacard.level_note(card, 'level2')}): {', '.join(ds.level2_values)}
- Level 3, table columns: {level3}
{f'- Samples: {said}' + chr(10) if said else ''}- Sample groups and timepoint columns, in time order: {subjects}
- Clusters: {ds.clusters[0]} .. {ds.clusters[-1]}
- Dashboard controls: {', '.join(a['control_words'] for a in controls().values())}"""


def plan_context(ds, dash_state, status="ok"):
    """What plan needs: what each view shows, then the data of each part (time axis, network
    settings ...), which the modules give. No background, no level value lists."""
    lines = [views_block(), "", "DATA"]
    for m in modules():
        if m.context:
            lines += [f"- {line}" for line in m.context(ds, dash_state)]
    if status == "use_current_selection":
        lines.append(f"- Clusters selected now: {', '.join(dash_state['selected_clusters'])}.")
    return "\n".join(lines)


PARSE = _with_modules(PARSE)
BREAKDOWN = _with_modules(BREAKDOWN)

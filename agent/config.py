"""Dataset description for the agent.

This is the one place to change when the agent is pointed at another
multi-level longitudinal dataset.
"""

from dataclasses import dataclass
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class LevelConfig:
    data_dir: Path = _REPO / "development" / "test_dashboard_input_csv"
    data_file: str = "cheesedata.csv"           # ID, timepoint columns, colour column
    labels_file: str = "cluster_labels.csv"     # one cluster number per row of data_file
    annotation_file: str = "pathchee.csv"       # ID plus the level columns
    network_file: str = "networkchee.csv"       # from, var_names (= to), weight

    id_col: str = "ID"
    color: str = "type"                         # ribbon line colour
    level1: str = "Pathway"                     # "Select a Functional Annotation"
    level2: str = "taxonomic.scope"             # "Select a Taxonomic Scope"
    level3: tuple = ("ID", "KEGG_ID", "GO_ID")  # table columns
    level3_notes: tuple = (                     # told to the LLM, one per level-3 column
        "contig / feature id, a number",
        "KEGG ortholog ids such as K03196",
        "GO term ids such as GO:0005524",
    )
    # Background knowledge told to the LLM. Replace it for another dataset.
    background: str = (
        "This is metagenomic data from two cheeses (sample groups A and C) sampled over ripening. "
        "Each feature is a contig. The data takes phylum as level 1 and class as level 2; "
        "level 3 is the contig itself with its KEGG and GO ids. Features are grouped into "
        "clusters by the shape of their trajectory."
    )
    level1_name: str = "phylum"                 # what the levels are called in questions
    level2_name: str = "class"
    missing: str = "-"                          # placeholder for "no annotation"
    cluster_prefix: str = "Group_"              # node ids in the dashboard
    subject_sep: str = "_"                      # A_1 -> subject A, timepoint 1


CONFIG = LevelConfig()

# Commands the D3 dashboard can replay today (inst/d3dashboard/js/agent.js).
SUPPORTED_COMMANDS = {
    "set filter1", "set filter2", "set importance", "set layout", "set view", "set colour",
    "brush node", "select node", "select all",
    "search table", "sort table", "clear table", "print message",
}

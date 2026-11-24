"""The fixed names of a MolPad dashboard, and the words filled in per dataset.

Nothing here belongs to one dataset. The column names are those the page fixes; what they
stand for comes from the study in the page (core/datacard.py).
"""

from dataclasses import dataclass

from .module import commands


@dataclass(frozen=True)
class LevelConfig:
    id_col: str = "ID"
    color: str = "type"                         # ribbon line colour
    level1: str = "Pathway"                     # level 1 of the filter bar
    level2: str = "taxonomic.scope"             # level 2 of the filter bar
    level3: tuple = ("ID",)                     # the id and the id columns of the table
    # The fields below are filled from the dataset card when the data is loaded.
    level3_notes: tuple = ()                    # told to the LLM, one per level-3 column
    background: str = ""
    level1_name: str = "functional annotation"  # what the levels are called in questions
    level2_name: str = "taxonomic scope"
    missing: str = "-"                          # placeholder for "no annotation"
    cluster_prefix: str = "Group_"              # node ids in the dashboard
    subject_sep: str = "_"                      # A_1 -> subject A, timepoint 1


# Commands the D3 dashboard can replay (inst/d3dashboard/js/agent.js): the actions of the
# modules, plus the chat's own "print message".
SUPPORTED_COMMANDS = set(commands()) | {"print message"}

"""The cheese case study as test data: the tables of the R workflow, saved as CSV files.

The tests and eval_trace run on it. It is the same data and the same study as in
dashboards/cheese/index.html (example.R), in a form that loads fast.
"""

from functools import lru_cache
from pathlib import Path

from agent.core.dataset import Dataset

FOLDER = Path(__file__).resolve().parents[2] / "development" / "test_dashboard_input_csv"

# The entries of gStudy() in example.R, as written into the page (for a level, "source" is
# the user's own column).
STUDY = {
    "background": "Metagenomic data from the surface of two washed-rind cheeses, sampled over ripening.",
    "feature": "contig",
    "level1": {"name": "phylum", "source": "phylum", "about": "the phylum a contig is assigned to"},
    "level2": {"name": "class", "source": "class", "about": "the class within that phylum"},
    "colour": {"source": "phylum"},
    "samples": {"groups": "Two kinds of cheese, A and C.",
                "time": "Sampling time points during ripening, aligned between the cheeses but with missing ones."},
}


@lru_cache(maxsize=None)
def cheese():
    return Dataset.from_csv(FOLDER, data="cheesedata.csv", labels="cluster_labels.csv",
                            annotation="pathchee.csv", network="networkchee.csv",
                            ids={"KEGG_ID": "KEGG", "GO_ID": "GO"}, description=STUDY)

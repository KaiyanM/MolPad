"""One folder per part of the dashboard. Each holds a module.json (what the part shows, which
controls it follows and sets, its features and the words people use for them) and the Python that
computes those features. agent/core/module.py loads them; ORDER is the order they are listed in."""

ORDER = ("filters", "clusters", "network", "stackbar", "ribbon", "table")

# What is reported about the clusters picked, in this order: size, course over time, level-2 mix,
# ids, edges.
DESCRIBE_ORDER = ("clusters", "ribbon", "stackbar", "table", "network")

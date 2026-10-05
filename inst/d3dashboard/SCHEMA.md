# MolPad D3 dashboard: data contract

The dashboard in this folder is a static page. It is driven entirely by one
JSON document that the host language (R today, possibly Python later) embeds
into `index.html`. Nothing else is required from the host: all filtering,
aggregation, layout and link rendering happen in the browser.

## How the page is assembled

`index.html` is a template with four placeholders:

| Placeholder | Replaced by |
|---|---|
| `{{TITLE}}` | the HTML-escaped title |
| `{{STYLES}}` | the files listed under `css` in `manifest.json`, either inlined in `<style>` tags or as `<link rel="stylesheet">` |
| `{{DATA_JSON}}` | the JSON document described below. Every `</` must be written as `<\/` so an embedded `</script>` cannot close the data tag |
| `{{SCRIPTS}}` | the files listed under `lib` then `js` in `manifest.json`, in that order, each in its own `<script>` tag (inline or `src`) |

Replace placeholders with plain string substitution, not regular expressions:
the JSON contains backslashes.

The page reads the data with
`JSON.parse(document.getElementById("molpad-data").textContent)`.

## JSON document

```jsonc
{
  "schema_version": 2,
  "title": "MolPad Dashboard",

  // Time point labels, in order. Each feature's "values" array is aligned
  // with this list.
  "timepoints": ["A_1", "A_2", "A_3", "C_1", "C_3"],

  // Optional (schema_version 2). Use [] or leave out when all time points
  // form one series. Otherwise each subject lists the entries of
  // "timepoints" that belong to it ("columns") and, aligned with them, their
  // labels on the shared time axis ("labels"). The ribbon plot then draws one
  // facet per subject, stacked top to bottom inside every cluster panel.
  "subjects": [
    { "name": "A", "columns": ["A_1", "A_2", "A_3"], "labels": ["1", "2", "3"] },
    { "name": "C", "columns": ["C_1", "C_3"],        "labels": ["1", "3"] }
  ],

  // Optional. The shared time axis, in order. Defaults to the union of the
  // subject labels in first-appearance order, or to "timepoints" when there
  // are no subjects.
  "time_labels": ["1", "2", "3"],

  // Values of the `type` column, in first-appearance order.
  "types": ["type_A", "type_B"],

  // Taxonomic scopes, in first-appearance order. The order fixes the
  // palette assignment and the stacking order of the bar chart.
  "taxa": ["enzymes", "antibodies"],

  // Functional annotations (Pathway), in first-appearance order. The first
  // one is selected when the page opens.
  "pathways": ["Nervous System", "Digestive System"],

  // All cluster labels (nodes). Should be the union of the clusters seen in
  // "features" and in "edges". Sorted by numeric suffix.
  "clusters": ["Group_1", "Group_2"],

  // Annotation columns to show in the table, in order. Every name listed
  // here must exist on each feature object.
  "annotation_columns": ["GO_ID", "KEGG_ID", "Pathway", "taxonomic.scope"],

  // Columns whose cell text holds database ids. Each id matched by `pattern`
  // (a JavaScript regular expression, applied globally) is rendered as a link
  // to `url` with `{id}` replaced. Use {} for no links.
  "id_links": {
    "GO_ID":   { "type": "GO",   "pattern": "GO:\\d{7}", "url": "https://www.ebi.ac.uk/QuickGO/term/{id}" },
    "KEGG_ID": { "type": "KEGG", "pattern": "K\\d{5}",   "url": "https://www.kegg.jp/entry/{id}" }
  },

  // One object per feature (row of the processed data).
  "features": [
    {
      "ID": "1",                       // string
      "cluster": "Group_2",            // one of "clusters"
      "type": "type_A",                // one of "types"
      "values": [-0.25, -0.68, 1.2, 0.4, -0.4], // aligned with "timepoints"; null for missing
      "GO_ID": "GO:0003674,GO:0003824",// annotation columns follow, as raw text
      "KEGG_ID": "K07124",
      "Pathway": "Nervous System",
      "taxonomic.scope": "enzymes"     // null allowed; such rows are left out of taxa views
    }
  ],

  // Network edges exactly as produced by gNetwork(): directed rows, both
  // directions may be present, weights may be negative or null. The page
  // collapses them to undirected edges, keeping the larger weight per pair,
  // drops null weights, and shows only edges with weight > slider value.
  "edges": [
    { "from": "Group_1", "to": "Group_2", "weight": 1.69, "IncNodePurity": 1.08 },
    { "from": "Group_2", "to": "Group_1", "weight": null }
  ],

  // Optional. Range of the "Importance Score" slider. When absent the page
  // uses min 0, max = 75th percentile of |weight| and value = median of
  // |weight|, each rounded to one decimal, matching the Shiny dashboard.
  "weight_slider": { "min": 0, "max": 3.2, "value": 1.0, "step": 0.1 }
}
```

## What the page derives from this

* **Node colour**: for the selected pathway, the number of features in each
  cluster whose `Pathway` equals it (0 for none), on a grey to green gradient.
* **Stacked bar**: number of features per selected cluster and taxonomic scope.
* **Ribbon plot**: for each selected cluster, subject and type, the minimum,
  mean and maximum of `values` at each time point (nulls ignored). The facets
  of one cluster share the time axis and the value axis.
* **Table**: the features of the selected clusters, filtered by taxonomic
  scope and by the table's own pathway filter, searchable and sortable, with a
  sort and filter menu on every column header.

## Writing the JSON from R

`MolPad:::d3_payload()` builds the list and `MolPad:::d3_payload_json()`
serialises it with `jsonlite::toJSON(auto_unbox = TRUE, dataframe = "rows",
na = "null")`. Array-valued top-level fields are wrapped in `I()` so a
single-element vector still becomes a JSON array.

## Writing the JSON from another language

Produce the structure above, read `manifest.json` for the file order, fill the
four placeholders of `index.html`, and write the result next to (or with) the
`css/`, `lib/` and `js/` folders. No build step is needed.

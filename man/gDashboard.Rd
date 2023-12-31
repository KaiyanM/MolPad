% Generated by roxygen2: do not edit by hand
% Please edit documentation in R/gDashboard.R
\docType{package}
\name{gDashboard}
\alias{gDashboard}
\title{Generate shiny dashboard}
\usage{
gDashboard(
  data,
  cluster,
  annotation,
  networkres,
  dashboardtitle = "MolPad Dashboard",
  id_colname = NULL,
  id_type = NULL
)
}
\arguments{
\item{data}{A dataframe; The output of \code{pre_process()}}

\item{cluster}{A list of two; The output of \code{gClusters()}}

\item{annotation}{A dataframe; The output of \code{gAnnotation()}}

\item{networkres}{A dataframe; The output of \code{gNetwork()}}

\item{dashboardtitle}{A string.}

\item{id_colname}{A single string or a sting vector. The column names in your annoation dataset that contains external database IDs.}

\item{id_type}{A single string or a sting vector. The corresponding database names for the above columns, must be choose from "KEGG" and "GO".}
}
\description{
Once you have the outputs from the g-functions, you're ready to create your custom Molpad dashboard. Be sure to specify the web ID columns and their corresponding column names.
}
\details{
Please ensure that columns containing external database IDs adhere to the following standards:
\itemize{
\item KEGG ID: Begin with 'K' followed by 5 digits, for example, K05685 or K06671.
\item GO ID: Begin with 'GO:' followed by 7 digits, such as GO:0003674."
}
}
\examples{
\dontrun{
data(test_data)
gDashboard(test_data_processed,test_cluster,test_annotations_processed,test_network,id_colname = c("GO_ID","KEGG_ID"),id_type = c("GO","KEGG"))
}
}

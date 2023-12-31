% Generated by roxygen2: do not edit by hand
% Please edit documentation in R/gNetwork_view.R
\docType{package}
\name{gNetwork_view}
\alias{gNetwork_view}
\title{View the feature importance plot}
\usage{
gNetwork_view(data)
}
\arguments{
\item{data}{A dataframe; The output of \code{gNetwork()}}
}
\description{
\code{gNetwork_view()} Generate a feature importance plot for the random forest result. This plot visually highlights the importance of individual cluster within a dataset, helping to identify key factors in predictive modeling.
}
\examples{
data(test_data)
gNetwork_view(test_network)
}

library(pkgdown)

pkgdown::build_site()

# create Readme.Rmd from https://github.com/krisrs1128/mbtransfer/blob/main/Readme.Rmd
# render using rmarkdown::render()
# rebuild site

# can customize css: https://raw.githubusercontent.com/krisrs1128/mbtransfer/main/_pkgdown.yml

library(usethis)
use_vignette("test_vignette")
rmarkdown::render("vignettes/test_vignette.Rmd")

setwd(paste0(getwd(),"/MolPad"))
pkgdown::build_site()

getwd()

setwd("/Users/hazelma/Documents/GitHub/MolPad/MolPad")

#----

# One time set-up with Git, Github, and Github Actions
usethis::use_git(message = "Initial commit")
usethis::use_github(private = FALSE)
usethis::use_github_action("pkgdown")
usethis::use_pkgdown_github_pages()

# locally building site
pkgdown::build_site()

# Install package
devtools::install_github("KaiyanM/MolPad")

usethis::use_pkgdown_github_pages()

pkgdown::build_site()

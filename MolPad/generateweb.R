library(pkgdown)

pkgdown::build_site()

# create Readme.Rmd from https://github.com/krisrs1128/mbtransfer/blob/main/Readme.Rmd
# render using rmarkdown::render()
# rebuild site

# can customize css: https://raw.githubusercontent.com/krisrs1128/mbtransfer/main/_pkgdown.yml

library(usethis)
use_vignette("test_vignette")
rmarkdown::render("vignettes/test_vignette.Rmd")

setwd(paste0(getwd(),"/pkg"))
pkgdown::build_site()


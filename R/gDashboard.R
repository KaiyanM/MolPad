#' gDashboard
#'
#' @description Run shiny dashboard.
#'
#' @docType package
#' @name gDashboard
#'
#' @param data The output of `pre_process()`
#' @param cluster The output of `gClusters()`
#' @param annotation A dataframe. The columns must include "ID", "taxonomic.scope",
#' and "Pathway".
#' @param networkres The output of `gNetwork`
#' @param dashboardtitle A string.
#' @param annotation A string. Choose a column in your dataset to add links for.
#'
#' @source scale()
#' @examples
#' data(FuncExample)
#' gDashboard(a, b, annotation, networkres, dashboardtitle = "My Title")
#' @importFrom shinydashboard dashboardHeader dashboardSidebar sidebarMenu menuItem
#' @importFrom shiny observe runApp fluidRow
#' @importFrom DT renderDataTable datatable dataTableOutput
#' @export
gDashboard <- function(data, cluster, annotation, networkres,
                       dashboardtitle = "MolPad Dashboard", 
                       id_type = "KEGG") {
  
  reshaped_df <- reshape_for_make_functions(data, cluster, annotation, id_type)

  uni_t <- unique(annotation$taxonomic.scope)
  uni_ptw <- unique(annotation$Pathway)
  css <- readLines(system.file("dashboard.css", package = "MolPad"))

  app <- list(
    ui =
      dashboardPage(
        dashboardHeader(title = dashboardtitle, titleWidth = 350),
        dashboardSidebar(
          width = 100,
          sidebarMenu(
            menuItem("Main", tabName = "dashboard", icon = icon("dashboard")),
            menuItem("Info", tabName = "widgets", icon = icon("eye"))
          )
        ),
        dashboardBody(
          tags$style(HTML(css)),
          tabItems(
            tabItem(
              tabName = "dashboard",
              fluidRow(
                box(column(4, selectInput("s_ptw", "Select a Functional Annotation:", uni_ptw)),
                  column(7, sliderInput("obs", "Importance Score:",
                    min = 0,
                    max = round(quantile(abs(networkres$weight))[4], 1),
                    value = round(quantile(abs(networkres$weight))[3], 1)
                  )),
                  plotOutput("plot", brush = brushOpts("plot_brush", fill = "#bd9fb7", stroke = "#85056d", opacity = 0.3), height = 410),
                  width = 7, height = 550
                ),
                tags$div(
                  id = "toto",
                  box(selectInput("s_tax", "Select a Taxonomic Scope:", uni_t, selected = NULL, multiple = TRUE),
                    plotOutput("plot3", height = 120),
                    plotOutput("plot2", height = 320),
                    width = 5, height = 550
                  )
                )
              ),
              fluidRow(
                tags$div(
                  id = "toto",
                  box(column(3, selectInput("s_p", "Filter by Functional Annotation:", uni_ptw, selected = as.factor(uni_ptw[1]))),
                    column(9, dataTableOutput("Observe_Out")),
                    width = 12
                  )
                )
              )
            ),
            tabItem(tabName = "widgets", h2("Info tab content"))
          )
        )
      ),
    server =
      function(input, output, session) {
        P1 <- reactive(
          make_the_graph(
            reshaped_df$output_graphptw,
            networkres,
            input$obs,
            input$s_ptw
          )
        )
        output$plot <- renderPlot(P1())

        group_names_selected <- reactive({
          if (is.null(input$plot_brush$xmin)) {
            "Group_2"
          } else {
            coords_filt()[, 1]
          }
        })

        taxa_selected <- reactive({
          if (is.null(input$s_tax)) {
            uni_t #unique(reshaped_df$output_maindata$taxonomic.scope)
          } else {
            input$s_tax
          }
        })

        output$plot2 <- renderPlot(
          make_line_plot(
            reshaped_df$output_maindata,
            group_names_selected(),
            taxa_selected()
          )
        )
        coords_filt <- reactive({
          if (is.null(input$plot_brush$xmin)) {
            make_the_table(P1())[, -c(1, 2)]
          } else {
            filter(
              make_the_table(P1()),
              x >= input$plot_brush$xmin,
              x <= input$plot_brush$xmax,
              y >= input$plot_brush$ymin,
              y <= input$plot_brush$ymax
            )[, -c(1:2)]
          }
        })

        output$plot3 <- renderPlot(
          make_stackbar_plot(
            reshaped_df$output_maindata,
            group_names_selected(),
            taxa_selected()
          )
        )

        observe({
          updateSelectInput(
            session,
            "s_p",
            choices = unique(info_filt()[, 5]), selected = input$s_ptw
          )
        })

        info_filt <- reactive({
          if (is.null((input$plot_brush$xmin))) {
            reshaped_df$output_tableview[reshaped_df$output_tableview$cluster %in% coords_filt()[, 1], ][1:10, ]
          } else {
            if (is.null(input$s_tax)) {
              reshaped_df$output_tableview[reshaped_df$output_tableview$cluster %in% coords_filt()[, 1], ]
            } else {
              reshaped_df$output_tableview[reshaped_df$output_tableview$cluster %in% coords_filt()[, 1], ] |> filter(taxonomic.scope %in% input$s_tax)
            }
          }
        })

        output$Observe_Out <- renderDataTable({
          info_filt2 <- info_filt() |>
            filter(Pathway %in% input$s_p) |>
            select(-c("Pathway"))
          datatable(info_filt2, escape = FALSE, options = list(pageLength = 5))
        })

        brushed_grp <- reactive({
          if (is.null(input$plot_brush$xmin)) {
            unique(networkres$from)
          } else {
            unique(coords_filt$name)
          }
        })
      }
  )
  runApp(app)
}

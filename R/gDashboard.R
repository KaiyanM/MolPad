#' Generate shiny dashboard
#'
#' @description Once you have the outputs from the g-functions, you're ready to create your custom Molpad dashboard. Be sure to specify the web ID columns and their corresponding column names.
#'
#' @docType package
#' @name gDashboard
#'
#' @param data A dataframe; The output of `pre_process()`
#' @param cluster A list of two; The output of `gClusters()`
#' @param annotation A dataframe; The output of `gAnnotation()`
#' @param networkres A dataframe; The output of `gNetwork()`
#' @param dashboardtitle A string.
#' @param id_colname A single string or a sting vector. The column names in your annoation dataset that contains external database IDs.
#' @param id_type A single string or a sting vector. The corresponding database names for the above columns, must be choose from "KEGG" and "GO".

#' @examples
#' \dontrun{
#' data(test_data)
#' gDashboard(test_data_processed,test_cluster,test_annotations_processed,test_network,id_colname = c("GO_ID","KEGG_ID"),id_type = c("GO","KEGG"))
#' }

#' @details
#' Please ensure that columns containing external database IDs adhere to the following standards:
#' * KEGG ID: Begin with 'K' followed by 5 digits, for example, K05685 or K06671.
#' * GO ID: Begin with 'GO:' followed by 7 digits, such as GO:0003674."
#' 
#' @importFrom shinydashboard dashboardPage dashboardHeader dashboardSidebar sidebarMenu menuItem tabItems tabItem box
#' @importFrom shiny observe runApp fluidRow icon tags HTML column selectInput sliderInput plotOutput brushOpts h3
#' @importFrom DT renderDataTable datatable dataTableOutput
#' @export
gDashboard <- function(data, cluster, annotation, networkres,
                       dashboardtitle = "MolPad Dashboard", 
                       id_colname=NULL, id_type=NULL) {
  
  reshaped_df <- reshape_for_make_functions(data, cluster, annotation,id_colname, id_type)

  uni_t <- unique(annotation$taxonomic.scope)
  uni_ptw <- unique(annotation$Pathway)
  css <- readLines(system.file("dashboard.css", package = "MolPad"))

  app <- list(
    ui =
      shinydashboard::dashboardPage(
        dashboardHeader(title = dashboardtitle, titleWidth = 350),
        dashboardSidebar(
          width = 100,
          sidebarMenu(
            menuItem("Main", tabName = "dashboard", icon = shiny::icon("gauge-high")),
            menuItem("Info", tabName = "info", icon = shiny::icon("eye"))
          )
        ),
        shinydashboard::dashboardBody(
          tags$style(HTML(css)),
          tabItems(
            tabItem(
              tabName = "dashboard",
              fluidRow(
                box(column(4, selectInput("s_ptw", "Select a Functional Annotation:", uni_ptw)),
                    column(2, selectInput("s_layout", "Graph Layout:", c("nicely","grid","star","circle","kk","drl","dh","gem","graphopt"))),
                  column(6, sliderInput("obs", "Importance Score:",
                    min = 0,
                    max = round(quantile(abs(networkres$weight),na.rm=TRUE)[4], 1),
                    value = round(quantile(abs(networkres$weight),na.rm=TRUE)[3], 1)
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
            tabItem(tabName = "info",
                    box(h3("Network Navigation"),br(),"Navigating the network in the MolPad dashboard follows three steps: ",
                        br(),br(),"1. Choose a primary functional annotation and adjust the edge density by tuning the threshold value on the importance score. Nodes that turnbright green represent clusters containing most features in the chosen functional annotation. ",
                        br(),br(),"2. Brushing on the network reveals patterns of taxonomic composition and typical trajectories. The user could also zoom into specific taxonomic annotations by filtering.",
                        br(),br(),"3. View the feature table and examine the drop-down options for other related function annotations, and then click the link for online information on the interested items. The interface is designed to support iterative exploration, encouraging the use of several steps to answer specific questions, like comparing the pattern distribution between two functions or finding functionally important community members metabolizing a feature of interest."
                        ,width = 10, height = 350),
                    box(h3("More Information"),br(),"Please check with our Github repository:",br(),br(),"KaiyanM/MolPad",width = 2, height = 350))
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
            input$s_ptw,
            input$s_layout
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
          datatable(info_filt2, escape = FALSE, options = list(pageLength = 5,
                                                               scrollX=TRUE,
                                                               autoWidth=TRUE))
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

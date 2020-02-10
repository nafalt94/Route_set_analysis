
def print_zones():

    sqlcall = "(SELECT * FROM emme_results)"
    uri.setDataSource("", sqlcall, "geom", "", "id")
    layer = QgsVectorLayer(uri.uri(), "result_impaiment " , "postgres")
    QgsProject.instance().addMapLayer(layer)


    values = (
        ('Not affected', -3, -3, QColor.fromRgb(0, 0, 200)),
        ('No route', -2, -2, QColor.fromRgb(0, 225, 200)),
        ('No route that is not affected', -1, -1, QColor.fromRgb(255, 0, 0)),
        ('Not searched', 0, 0, QColor.fromRgb(255, 255, 255)),
        ('Alternative route exists', 0, 1000, QColor.fromRgb(102, 255, 102)),
    )

    # create a category for each item in values
    ranges = []
    for label, lower, upper, color in values:
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        symbol.setColor(QColor(color))
        rng = QgsRendererRange(lower, upper, symbol, label)
        ranges.append(rng)

    ## create the renderer and assign it to a layer
    expression = 'alt_route_cost' # field name
    layer.setRenderer(QgsGraduatedSymbolRenderer(expression, ranges))
    #iface.mapCanvas().refresh()


def print_lines():
    # sqlcall = "(SELECT * FROM od_lines)"
    # uri.setDataSource("", sqlcall, "geom", "", "geom")
    # layer = QgsVectorLayer(uri.uri(), "od_lines ", "postgres")
    # QgsProject.instance().addMapLayer(layer)
    #
    # ## create the renderer and assign it to a layer
    # expression = 'geom'  # field name
    # layer.setRenderer(QgsGraduatedSymbolRenderer(expression, ranges))
    # # iface.mapCanvas().refresh()

    sqlcall = "(SELECT * FROM od_lines )"
    uri.setDataSource("", sqlcall, "geom", "", "geom")
    layert = QgsVectorLayer(uri.uri(), " test ", "postgres")
    QgsProject.instance().addMapLayer(layert)



#Remove old layers
removeRoutesLayers()

print_zones()
print_lines()

#Remove old layers
removeRoutesLayers()

sqlcall = "(SELECT * FROM emme_results)"
uri.setDataSource("", sqlcall, "geom", "", "id")
layer = QgsVectorLayer(uri.uri(), "test " , "postgres")
QgsProject.instance().addMapLayer(layer)


values = (
    ('Zon påverkas ej', -3, -3, QColor.fromRgb(0, 0, 200)),
    ('No route', -2, -2, QColor.fromRgb(0, 225, 200)),
    ('No route that is not affected', -1, -1, QColor.fromRgb(255, 0, 0)),
    ('Not searched', 0, 0, QColor.fromRgb(255, 255, 255)),
    ('Improves', 0, 1000, QColor.fromRgb(102, 255, 102)),
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
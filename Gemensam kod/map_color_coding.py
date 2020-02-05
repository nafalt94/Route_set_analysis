nr_routes = 1

sqlcall = "(SELECT * FROM emme_zones)"
uri.setDataSource("", sqlcall, "geom", "", "id")
layer = QgsVectorLayer(uri.uri(), "test " , "postgres")
QgsProject.instance().addMapLayer(layer)

#renderer = layer.renderer()
#print("Type:", renderer.type())
#
#layer.renderer().symbol().symbolLayer(0).setColor(QColor.fromRgb(0, 225, 0))
#
## update legend for layer
#qgis.utils.iface.layerTreeView().refreshLayerSymbology(layer.id())
#
#print(layer.renderer().symbol().symbolLayers()[0].properties())
#
#symbols = layer.renderer().symbol()


#####################################
values = (
    ('Low', 6772, 7520, QColor.fromRgb(0, 225, 0)),
    ('Medium', 7520, 7620, 'yellow'),
    ('Large', 7620, 240000, 'orange'),
)

# create a category for each item in values
ranges = []
for label, lower, upper, color in values:
    symbol = QgsSymbol.defaultSymbol(layer.geometryType())
    symbol.setColor(QColor(color))
    rng = QgsRendererRange(lower, upper, symbol, label)
    ranges.append(rng)
    
## create the renderer and assign it to a layer
expression = 'id' # field name
layer.setRenderer(QgsGraduatedSymbolRenderer(expression, ranges))
#iface.mapCanvas().refresh() 
#################################################

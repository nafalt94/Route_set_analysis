import time
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtSql import *
from PyQt5.QtWidgets import *
from qgis.core import QgsFeature, QgsGeometry, QgsProject
from shapely import wkb

print(__name__)


# Function definition

def TicTocGenerator():
    # Generator that returns time differences
    ti = 0  # initial time
    tf = time.time()  # final time
    while True:
        ti = tf
        tf = time.time()
        yield tf - ti  # returns the time difference


def toc(tempBool=True):
    # Prints the time difference yielded by generator instance TicToc
    tempTimeInterval = next(TicToc)
    if tempBool:
        print("Elapsed time: %f seconds.\n" % tempTimeInterval)


def tic():
    # Records a time in TicToc, marks the beginning of a time interval
    toc(False)


def removeRoutesLayers():
    layers = QgsProject.instance().mapLayers()

    for layer_id, layer in layers.items():
        if str(layer.name()) != "model_graph" and str(layer.name()) != "emme_zones" and str(layer.name()) != "labels" \
                and str(layer.name()) != "OpenStreetMap" and str(layer.name()) != "all_results" and str(
            layer.name()) != "Centroider" and str(layer.name()) != "dijk_result_table" and str(
            layer.name()) != "ata_lid" and str(layer.name()) != "result_table":
            QgsProject.instance().removeMapLayer(layer.id())


# Prints a route set based on whats in result_table.
def printRoutes():
    i = 1
    # WHERE rejoin_link=0   insert into to print
    query = db.exec_("SELECT MAX(did) FROM result_table")
    query.next()
    print(query.value(0))
    nr_routes = query.value(0)
    lid_list_q = db.exec_("SELECT result_table.lid, foo.count FROM result_table INNER JOIN (SELECT count(*), lid \
    FROM result_table WHERE not did=(-1) group by lid) as foo ON(result_table.lid = foo.lid) WHERE not did=(-1) \
    group by result_table.lid, foo.count")
    lid_list = []
    lid_count = []
    while lid_list_q.next():
        lid_list.append(lid_list_q.value(0))
        lid_count.append(lid_list_q.value(1))

    # Källa https://sashat.me/2017/01/11/list-of-20-simple-distinct-colors/
    color_list = [QColor.fromRgb(128, 0, 0), QColor.fromRgb(170, 10, 40), QColor.fromRgb(128, 128, 0),
                  QColor.fromRgb(0, 128, 128), QColor.fromRgb(0, 0, 128), QColor.fromRgb(0, 0, 0),
                  QColor.fromRgb(230, 25, 75), QColor.fromRgb(245, 130, 48), QColor.fromRgb(255, 255, 25),
                  QColor.fromRgb(210, 245, 60), QColor.fromRgb(60, 180, 75), QColor.fromRgb(70, 240, 240),
                  QColor.fromRgb(0, 130, 200), QColor.fromRgb(145, 30, 180), QColor.fromRgb(240, 50, 230),
                  QColor.fromRgb(128, 128, 128), QColor.fromRgb(250, 190, 190), QColor.fromRgb(255, 215, 180),
                  QColor.fromRgb(255, 250, 200), QColor.fromRgb(170, 255, 195)]
    bad_color = ['Maroon', 'Magenta', 'Olive', 'Orange', 'Navy', 'Black', 'Red', 'Teal', 'Blue', 'Lime', 'Cyan', 'Green'
        , 'Brown', 'Purple', 'Yellow', 'Grey', 'Pink', 'Apricot', 'Beige', 'Mint', 'Lavender']

    lid_c = []
    # while lid_query.next():
    while i <= nr_routes:

        dummy_q = db.exec_(
            "SELECT did, lid, ST_astext(geom) as geom FROM result_table WHERE not did=(-1) and result_table.did =" + str(
                i))
        layert = QgsVectorLayer("MultiLineString?crs=epsg:3006", " route " + str(i), "memory")
        QgsProject.instance().addMapLayer(layert)

        featurelist = []
        while dummy_q.next():
            lid = dummy_q.value(1)
            seg = QgsFeature()
            j = 0
            while j < len(lid_list):
                if lid == lid_list[j]:
                    lid_nr = j
                j += 1
            # print("lid nr is:"+str(lid_nr)+ " lid is :"+str(lid_list[lid_nr])+" lid count is:"+str(lid_count[lid_nr]))
            nr_included = 0
            dummy = 0
            j = 0
            while j < len(lid_c):
                if lid == lid_c[j]:
                    nr_included += 1
                j += 1
            # if dummy < nr_included:
            #     dummy = nr_included
            lid_c.append(lid)
            if lid_count[lid_nr] == 1:
                offset = 0
            else:
                if lid_count[lid_nr] % 2 == 0:
                    # Even
                    off = (-lid_count[lid_nr] / 2) + nr_included
                    if off == 0:
                        offset = ((-lid_count[lid_nr] / 2) + nr_included + 1) * 200
                    else:
<<<<<<< HEAD
                        offset = ((-lid_count[lid_nr]/2) + nr_included)*200
=======
                        offset = ((-lid_count[lid_nr] / 2) + nr_included) * 80
>>>>>>> b69948db6665ed5f30d2925c9356500bdac0da03

                else:
                    # Odd
                    print("odd value is :", (-lid_count[lid_nr] / 2) + nr_included)
                    print("odd value rounded is :", int((-lid_count[lid_nr] / 2) + nr_included))
<<<<<<< HEAD
                    offset = int(((-lid_count[lid_nr]/2) + nr_included)*200)
                    print("odd ",offset)
=======
                    offset = int(((-lid_count[lid_nr] / 2) + nr_included) * 80)
                    print("odd ", offset)
>>>>>>> b69948db6665ed5f30d2925c9356500bdac0da03

            seg.setGeometry(QgsGeometry.fromWkt(dummy_q.value(2)).offsetCurve(offset, 1, 1, 2.0))
            featurelist.append(seg)

        symbol = QgsLineSymbol.createSimple({'color': bad_color[i], 'width': '0.4'})
        renderers = layert.renderer()
        renderers.setSymbol(symbol.clone())
        qgis.utils.iface.layerTreeView().refreshLayerSymbology(layert.id())
        single_symbol_renderer = layert.renderer()
        symbol = single_symbol_renderer.symbol()
        symbol.setWidth(0.8)

        layert.dataProvider().addFeatures(featurelist)
        layert.triggerRepaint()
        i += 1
        print("route nr", i - 1)
        print("nr included max ", dummy)

    # Start node
    start_q = db.exec_("SELECT lid, ST_astext(ST_PointN(the_geom,1)) AS start \
        FROM (SELECT lid, (ST_Dump(geom)).geom As the_geom \
        FROM result_table WHERE did=1 and path_seq=1) As foo")
    start_q.next()
    layer = QgsVectorLayer('Point?crs=epsg:3006', 'Start', 'memory')
    # Set the provider to accept the data source
    prov = layer.dataProvider()
    # Add a new feature and assign the geometry
    feat = QgsFeature()
    feat.setGeometry(QgsGeometry.fromWkt(start_q.value(1)))
    prov.addFeatures([feat])
    # Update extent of the layer
    layer.updateExtents()
    # Add the layer to the Layers panel
    QgsProject.instance().addMapLayer(layer)
    single_symbol_renderer = layer.renderer()
    symbol1 = single_symbol_renderer.symbol()
    symbol1.setColor(QColor.fromRgb(0, 225, 0))
    symbol1.setSize(3)
    # more efficient than refreshing the whole canvas, which requires a redraw of ALL layers
    layer.triggerRepaint()
    # update legend for layer
    qgis.utils.iface.layerTreeView().refreshLayerSymbology(layer.id())

    # End Node
    end_q = db.exec_("SELECT lid, ST_astext(ST_PointN(the_geom,-1)) AS start FROM (SELECT lid, (ST_Dump(geom)).geom As the_geom \
    FROM result_table  WHERE path_seq = (SELECT max(path_seq) FROM result_table WHERE did=1) and did=1) AS foo")
    end_q.next()
    layere = QgsVectorLayer('Point?crs=epsg:3006', 'End', 'memory')
    # Set the provider to accept the data source
    prov = layere.dataProvider()
    # Add a new feature and assign the geometry
    feat = QgsFeature()
    feat.setGeometry(QgsGeometry.fromWkt(end_q.value(1)))
    prov.addFeatures([feat])
    # Update extent of the layer
    layere.updateExtents()
    # Add the layer to the Layers panel
    QgsProject.instance().addMapLayer(layere)
    single_symbol_renderer = layere.renderer()
    symbol = single_symbol_renderer.symbol()
    symbol.setColor(QColor.fromRgb(255, 0, 0))
    symbol.setSize(3)
    layere.triggerRepaint()
    qgis.utils.iface.layerTreeView().refreshLayerSymbology(layere.id())


def printRoutesRejoin():
    i = 1
    # WHERE rejoin_link=0   insert into to print
    query = db.exec_("SELECT MAX(did) FROM result_table")
    query.next()
    nr_routes = query.value(0)

    # Källa https://sashat.me/2017/01/11/list-of-20-simple-distinct-colors/
    color_list = [QColor.fromRgb(128, 0, 0), QColor.fromRgb(170, 10, 40), QColor.fromRgb(128, 128, 0),
                  QColor.fromRgb(0, 128, 128), QColor.fromRgb(0, 0, 128), QColor.fromRgb(0, 0, 0),
                  QColor.fromRgb(230, 25, 75), QColor.fromRgb(245, 130, 48), QColor.fromRgb(255, 255, 25),
                  QColor.fromRgb(210, 245, 60), QColor.fromRgb(60, 180, 75), QColor.fromRgb(70, 240, 240),
                  QColor.fromRgb(0, 130, 200), QColor.fromRgb(145, 30, 180), QColor.fromRgb(240, 50, 230),
                  QColor.fromRgb(128, 128, 128), QColor.fromRgb(250, 190, 190), QColor.fromRgb(255, 215, 180),
                  QColor.fromRgb(255, 250, 200), QColor.fromRgb(170, 255, 195)]
    bad_color = ['Maroon', 'Magenta', 'Olive', 'Orange', 'Navy', 'Black', 'Red', 'Teal', 'Blue', 'Lime', 'Cyan', 'Green'
        , 'Brown', 'Purple', 'Yellow', 'Grey', 'Pink', 'Apricot', 'Beige', 'Mint', 'Lavender']

    while i <= nr_routes:
        # Routes without offset
        sqlcall = "(select lid, did, geom from result_table where lid in (select lid from result_table group by lid having \
               count(*) = 1) and did =" + str(i) + " and rejoin_link=0 group by lid, did, geom ORDER BY lid, did)"
        uri.setDataSource("", sqlcall, "geom", "", "lid")
        layert = QgsVectorLayer(uri.uri(), " route " + str(i), "postgres")
        QgsProject.instance().addMapLayer(layert)
        symbol = QgsLineSymbol.createSimple({'color': bad_color[i],
                                             'width': '0.6',
                                             'offset': '0'})
        renderers = layert.renderer()
        renderers.setSymbol(symbol.clone())
        qgis.utils.iface.layerTreeView().refreshLayerSymbology(layert.id())
        # single_symbol_renderer = layert.renderer()
        # symbol = single_symbol_renderer.symbol()
        # symbol.setWidth(0.8)

        # Routes in need of offset
        sqlcall = "(select lid, did, geom from result_table where lid in (select lid from result_table \
               group by lid having count(*) > 1) and did=" + str(
            i) + " and rejoin_link=0 group by lid, did, geom ORDER BY lid, did)"
        uri.setDataSource("", sqlcall, "geom", "", "lid")
        layert = QgsVectorLayer(uri.uri(), " route " + str(i), "postgres")
        QgsProject.instance().addMapLayer(layert)
        if i == 1:
            offset = 0
        else:
            offset = i - i * 0.7
        print("i is " + str(i) + " and offset is:" + str(offset))
        symbol = QgsLineSymbol.createSimple({'color': bad_color[i],
                                             'width': '0.4',
                                             'offset': str(offset)})
        renderers = layert.renderer()
        renderers.setSymbol(symbol.clone())
        qgis.utils.iface.layerTreeView().refreshLayerSymbology(layert.id())

        # single_symbol_renderer = layert.renderer()
        # symbol = single_symbol_renderer.symbol()
        # symbol.setWidth(0.8)

        #
        # if i < len(color_list):
        #     symbol.setColor(color_list[i])
        #     layert.triggerRepaint()
        #     qgis.utils.iface.layerTreeView().refreshLayerSymbology(layert.id())
        #
        i = i + 1

    # Start node
    start_q = db.exec_("SELECT lid, ST_astext(ST_PointN(the_geom,1)) AS start \
           FROM (SELECT lid, (ST_Dump(geom)).geom As the_geom \
           FROM result_table WHERE did=1 and path_seq=1) As foo")
    start_q.next()
    layer = QgsVectorLayer('Point?crs=epsg:3006', 'Start', 'memory')

    # Set the provider to accept the data source
    prov = layer.dataProvider()

    # Add a new feature and assign the geometry
    feat = QgsFeature()
    feat.setGeometry(QgsGeometry.fromWkt(start_q.value(1)))
    prov.addFeatures([feat])

    # Update extent of the layer
    layer.updateExtents()

    # Add the layer to the Layers panel
    QgsProject.instance().addMapLayer(layer)

    single_symbol_renderer = layer.renderer()
    symbol = single_symbol_renderer.symbol()
    symbol.setColor(QColor.fromRgb(0, 225, 0))
    symbol.setSize(3)
    # more efficient than refreshing the whole canvas, which requires a redraw of ALL layers
    layer.triggerRepaint()
    # update legend for layer
    qgis.utils.iface.layerTreeView().refreshLayerSymbology(layer.id())

    # End Node
    end_q = db.exec_("SELECT lid, ST_astext(ST_PointN(the_geom,-1)) AS start FROM (SELECT lid, (ST_Dump(geom)).geom As the_geom \
       FROM result_table  WHERE path_seq = (SELECT max(path_seq) FROM result_table WHERE did=1) and did=1) AS foo")
    end_q.next()
    layere = QgsVectorLayer('Point?crs=epsg:3006', 'END', 'memory')

    # Set the provider to accept the data source
    prov = layere.dataProvider()

    # Add a new feature and assign the geometry
    feat = QgsFeature()
    feat.setGeometry(QgsGeometry.fromWkt(end_q.value(1)))
    prov.addFeatures([feat])

    # Update extent of the layer
    layere.updateExtents()

    # Add the layer to the Layers panel
    QgsProject.instance().addMapLayer(layere)

    single_symbol_renderer = layere.renderer()
    symbol = single_symbol_renderer.symbol()
    symbol.setColor(QColor.fromRgb(255, 0, 0))
    symbol.setSize(3)

    layer.triggerRepaint()
    qgis.utils.iface.layerTreeView().refreshLayerSymbology(layere.id())


# det jag behöver få från databasen start_list, end_list, lids
def print_selected_pairs():
    # Removes layers not specified in removeRoutesLayers
    removeRoutesLayers()

    # Get list and removed lids
    lids = []
    temp_query1 = db.exec_("SELECT * FROM removed_lids")

    while temp_query1.next():
        lids.append(temp_query1.value(0))

    temp_query2 = db.exec_("SELECT DISTINCT start_zone AS start_zones, end_zone AS end_zones FROM all_results")
    start_list = []
    end_list = []

    while temp_query2.next():
        start_list.append(temp_query2.value(0))
        end_list.append(temp_query2.value(1))

    # first it creates neccessary db-tables for visualization of the OD-pairs in star_list and end_list
    # Create OD_lines table
    db.exec_("DROP table if exists OD_lines")
    db.exec_("SELECT ST_MakeLine(ST_Centroid(geom) ORDER BY id) AS geom into od_lines "
             "FROM emme_zones where id = " + str(start_list[0]) + " OR id = " + str(end_list[0]) + "")

    # Create emme_result table
    db.exec_("DROP table if exists emme_results")
    db.exec_("SELECT 0.0 as alt_route_cost,* INTO emme_results FROM emme_zones")

    i = 0
    while i < len(start_list):
        if i > 0:
            db.exec_("INSERT INTO OD_lines(geom) SELECT ST_MakeLine(ST_Centroid(geom) ORDER BY id) "
                     "AS geom FROM emme_zones where id = " + str(start_list[i]) + " OR id = " + str(end_list[i]) + "")

        result_test = odEffect(start_list[i], end_list[i], lids)
        print("Result of " + str(i) + " is: " + str(result_test))
        db.exec_(
            "UPDATE emme_results SET alt_route_cost = " + str(result_test) + " WHERE id = '" + str(start_list[i]) + "'"
                                                                                                                    " OR id = '" + str(
                end_list[i]) + "';")

        i += 1

    db.exec_("ALTER TABLE OD_lines ADD COLUMN id SERIAL PRIMARY KEY;")

    sqlcall = "(SELECT * FROM emme_results)"
    uri.setDataSource("", sqlcall, "geom", "", "id")
    layer = QgsVectorLayer(uri.uri(), "result_deterioration ", "postgres")
    QgsProject.instance().addMapLayer(layer)

    values = (
        ('Not affected', -3, -3, QColor.fromRgb(0, 0, 200)),
        ('No route', -2, -2, QColor.fromRgb(0, 225, 200)),
        ('No route that is not affected', -1, -1, QColor.fromRgb(255, 0, 0)),
        ('Not searched', 0, 0, QColor.fromRgb(255, 255, 255)),
        ('Alternative route: 1-10 % deterioration', 0, 1.1, QColor.fromRgb(102, 255, 102)),
        ('Alternative route: 10-100 % deterioration', 1.1, 1000, QColor.fromRgb(255, 255, 0)),
    )

    # create a category for each item in values
    ranges = []
    for label, lower, upper, color in values:
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        symbol.setColor(QColor(color))
        rng = QgsRendererRange(lower, upper, symbol, label)
        ranges.append(rng)

    ## create the renderer and assign it to a layer
    expression = 'alt_route_cost'  # field name
    layer.setRenderer(QgsGraduatedSymbolRenderer(expression, ranges))
    # iface.mapCanvas().refresh()

    # Print lines from od_lines
    sqlcall = "(SELECT * FROM od_lines )"
    uri.setDataSource("", sqlcall, "geom", "", "id")
    layert = QgsVectorLayer(uri.uri(), " OD_pairs ", "postgres")
    QgsProject.instance().addMapLayer(layert)


# Ska hämtas från databasen list,removed_lids
def allToAll():
    # Removes layers not specified in removeRoutesLayers
    removeRoutesLayers()

    # Get list and removed lids
    removed_lids = []
    temp_query1 = db.exec_("SELECT * FROM removed_lids")

    while temp_query1.next():
        removed_lids.append(temp_query1.value(0))

    temp_query2 = db.exec_("SELECT DISTINCT start_zone AS start_zones FROM all_results")

    list = []
    while temp_query2.next():
        list.append(temp_query2.value(0))

    removed_lid_string = "( lid = " + str(removed_lids[0])
    i = 1
    while i < len(removed_lids):
        removed_lid_string += " or lid =" + str(removed_lids[i])
        i += 1
    removed_lid_string += ")"

    # Queryn skapar tabell för alla länkar som går igenom removed_lid
    db.exec_("DROP TABLE IF EXIST temp_test")
    db.exec_(
        " select * into temp_test from all_results f where exists(select 1 from all_results l where " + removed_lid_string + " and"
                                                                                                                             " (f.start_zone = l.start_zone and f.end_zone = l.end_zone and f.did = l.did))")

    # Här vill jag skapa nytt lager som visar intressanta saker för varje zon
    # Create emme_result table
    db.exec_("DROP table if exists emme_results")
    db.exec_(
        "SELECT 0 as nr_non_affected, 0 as nr_no_routes, 0 as nr_all_routes_affected, 0.0 as mean_deterioration, 0 as nr_pairs,* INTO emme_results FROM emme_zones")

    i = 0
    while i < len(list):
        result = analysis_multiple_zones(list[i], list, removed_lids)
        db.exec_("UPDATE emme_results SET nr_non_affected = " + str(result[0]) + " , nr_no_routes = " +
                 str(result[1]) + " , nr_all_routes_affected = " + str(result[2]) + " , mean_deterioration = " +
                 str(result[3]) + " , nr_pairs = " + str(result[4]) + " WHERE id = " +
                 str(list[i]) + ";")
        i += 1

    ############################ Create layer for mean deterioration
    sqlcall = "(SELECT * FROM emme_results)"
    uri.setDataSource("", sqlcall, "geom", "", "id")

    layer = QgsVectorLayer(uri.uri(), "mean_deterioration ", "postgres")
    QgsProject.instance().addMapLayer(layer)

    values = (
        ('Not searched', 0, 0, QColor.fromRgb(255, 255, 255)),
        ('No deterioration', -1, -1, QColor.fromRgb(153, 204, 255)),
        ('Mean deterioration 1-20% ', 0, 1.2, QColor.fromRgb(102, 255, 102)),
        ('Mean deterioration 20-30% ', 1.2, 1.3, QColor.fromRgb(255, 255, 153)),
        ('Mean deterioration 30-50% ', 1.3, 1.5, QColor.fromRgb(255, 178, 102)),
        ('Mean deterioration 50-100% ', 1.5, 100, QColor.fromRgb(255, 102, 102)),
    )

    # create a category for each item in values
    ranges = []
    for label, lower, upper, color in values:
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        symbol.setColor(QColor(color))
        rng = QgsRendererRange(lower, upper, symbol, label)
        ranges.append(rng)

    ## create the renderer and assign it to a layer
    expression = 'mean_deterioration'  # field name
    layer.setRenderer(QgsGraduatedSymbolRenderer(expression, ranges))

    ############################ Create layer for nr_affected OD-pairs
    sqlcall = "(select CASE WHEN nr_pairs > 0 THEN cast((nr_pairs - nr_non_affected) as float)/nr_pairs " \
              "ELSE 100 END as prop_affected,* from emme_results)"
    uri.setDataSource("", sqlcall, "geom", "", "id")

    layer = QgsVectorLayer(uri.uri(), "prop_affected ", "postgres")
    QgsProject.instance().addMapLayer(layer)

    values = (
        ('Not searched', 1, 100, QColor.fromRgb(255, 255, 255)),
        ('0% affected pairs', 0, 0, QColor.fromRgb(153, 204, 255)),
        ('1-20% affected pairs', 0, 0.2, QColor.fromRgb(102, 255, 102)),
        ('20-30% affected pairs', 0.2, 0.3, QColor.fromRgb(255, 255, 153)),
        ('30-50% affected pairs', 0.3, 0.5, QColor.fromRgb(255, 178, 102)),
        ('50-100% affected pairs', 0.5, 1, QColor.fromRgb(255, 102, 102)),
    )

    # create a category for each item in values
    ranges = []
    for label, lower, upper, color in values:
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        symbol.setColor(QColor(color))
        rng = QgsRendererRange(lower, upper, symbol, label)
        ranges.append(rng)

    ## create the renderer and assign it to a layer
    expression = 'prop_affected'  # field name
    layer.setRenderer(QgsGraduatedSymbolRenderer(expression, ranges))


def odEffect(start, end, lids):
    start_zone = start
    end_zone = end

    removed_lid_string = "( lid = " + str(lids[0])
    i = 1
    while i < len(lids):
        removed_lid_string += " or lid =" + str(lids[i])
        i += 1
    removed_lid_string += ")"

    # Finding best, non-affected alternative route
    query1 = db.exec_("SELECT MIN(did) FROM all_results WHERE"
                      " start_zone = " + str(start_zone) + " AND end_zone = " + str(end_zone) + " AND "
                                                                                                " did NOT IN (select did from all_results where start_zone = " + str(
        start_zone) + " AND end_zone = " + str(end_zone) + " AND  " + removed_lid_string + ")")

    query1.next()
    id_alt = str(query1.value(0))
    # print("id_alt är: "+ id_alt)

    if id_alt == "NULL":
        # Either there's only one route in the route set or the route set is empty
        query = db.exec_(
            "SELECT MIN(did) FROM all_results where start_zone = " + str(start_zone) + " AND end_zone = " + str(
                end_zone) + "")
        query.next()

        if query.value(0):
            # There is no route that is not affected
            return -1
        else:
            # There is no routes with that start and end zone
            return -2;

    elif id_alt == "1":
        # print("Zon påverkas inte")
        return -3
    else:
        # print("Zon påverkas och bästa id är:" + id_alt)

        # Fetching cost of the optimal route and the alternative
        query2 = db.exec_("SELECT sum(link_cost) from all_results where "
                          " (start_zone = " + str(start_zone) + " AND end_zone = " + str(end_zone) + ") AND "
                                                                                                     "(did = 1 OR did = " + str(
            id_alt) + ") group by did")
        query2.next()
        # Best cost
        cost_opt = str(query2.value(0))

        # Alternative cost
        query2.next()
        cost_alt = str(query2.value(0))

        # Proportion of extra cost of alternative route in relation to opt route
        # print("cost_opt = " + cost_opt + " and cost_alt = " + cost_alt)
        return float(cost_alt) / float(cost_opt)


def analysis_multiple_zones(start_node, list, lids):
    count3 = 0
    count2 = 0
    count1 = 0
    count_detour = 0
    sum_detour = 0

    i = 0
    while i < len(list):
        if start_node != list[i]:
            result_test = odEffect(start_node, list[i], lids)

            if result_test == -3:
                count3 += 1
            elif result_test == -2:
                count2 += 1
            elif result_test == -1:
                count1 += 1
            else:
                count_detour += 1
                sum_detour += result_test
        i = i + 1

        if count_detour != 0:
            mean_detour = sum_detour / count_detour
        else:
            mean_detour = -1
    return [count3, count2, count1, mean_detour, i - 1]


# End of function definition


# Initialize TicToc function.
TicToc = TicTocGenerator()

# DATABASE CONNECTION ------------------------------------------------------
uri = QgsDataSourceUri()
# set host name, port, database name, username and password
uri.setConnection("localhost", "5432", "exjobb", "postgres", "password123")
print(uri.uri())
db = QSqlDatabase.addDatabase('QPSQL')

if db.isValid():
    print("QPSQL db is valid")
    db.setHostName(uri.host())
    db.setDatabaseName(uri.database())
    db.setPort(int(uri.port()))
    db.setUserName(uri.username())
    db.setPassword(uri.password())
    # open (create) the connection
    if db.open():
        print("Opened %s" % uri.uri())
    else:
        err = db.lastError()
        print(err.driverText())


# DATABASE CONNECTION COMPLETE ---------------------------------------------

def main():
    tic()
    if db.isValid:
        removeRoutesLayers()

        # Create layer for one route set (run routeSetGeneration before).
        # printRoutes()
        # printRoutesRejoin()

        # Creates new visualisation layer for selected pairs (run selectedODResultTable before).
        print_selected_pairs()

        # All to all visualisation for all pairs in list (run AllToAllResultTable before).
        # allToAll()

    toc()


if __name__ == "__main__" or __name__ == "__console__":
    main()
db.close()


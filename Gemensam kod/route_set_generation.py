import time
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtSql import *
from PyQt5.QtWidgets import *
from qgis.core import QgsFeature, QgsGeometry, QgsProject

print(__name__)


# Function definitions

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


# Initialize TicToc function.
TicToc = TicTocGenerator()


# Compare if to var1/var2 < t
def comp(var1, var2, t):
    if var1 / var2 < t:
        return True
    else:
        return False


# Remove all GIS-layers except those stated in the function.
def removeRoutesLayers():
    layers = QgsProject.instance().mapLayers()

    for layer_id, layer in layers.items():
        if str(layer.name()) != "model_graph" and str(layer.name()) != "emme_zones" and str(layer.name()) != "labels" \
                and str(layer.name()) != "OpenStreetMap" and str(layer.name()) != "all_results" and str(
            layer.name()) != "Centroider" and str(layer.name()) != "dijk_result_table" and str(layer.name()) != "ata_lid":
            QgsProject.instance().removeMapLayer(layer.id())


# Give a zone id get a node id
def genonenode(zone):
    db.exec_("CREATE TABLE IF NOT EXISTS od_lid AS (SELECT * FROM(SELECT ROW_NUMBER() OVER (PARTITION BY id \
                ORDER BY id, distance) AS score, id, lid, start_node, distance \
                FROM(SELECT emme.id, lid, start_node, ST_distance(geom, emme_centroid) AS \
                distance FROM model_graph, (SELECT id, ST_centroid(geom) AS \
                emme_centroid, geom AS emme_geom FROM emme_zones WHERE id > 0) AS emme \
                WHERE ST_Intersects(geom, emme_geom) ORDER BY distance) AS subq) AS subq \
                WHERE score = 1)")

    query1 = db.exec_("SELECT start_node FROM od_lid WHERE id=" + str(zone))
    counter1 = 0

    # Saving SQL answer into matrix
    while query1.next():
        counter1 += 1
        # print("node is :" + str(query1.value(0)))
        node = query1.value(0)

    if counter1 != 1:
        raise Exception('No  node in Zones and startnode is:' + str(zone))

    return node


# Generates a route set between two zone id:s.
def routeSetGeneration(start_zone, end_zone, my, threshold):
    db.exec_("CREATE TABLE IF NOT EXISTS cost_table AS (select ST_Length(geom)/speed*3.6 AS link_cost, * \
    from model_graph)")

    db.exec_("CREATE TABLE IF NOT EXISTS all_results(start_zone INT, end_zone INT,did INT, seq INT, path_seq INT, \
        node BIGINT,edge BIGINT,cost DOUBLE PRECISION,agg_cost DOUBLE PRECISION, \
        link_cost DOUBLE PRECISION, id INT, geom GEOMETRY, lid BIGINT, start_node BIGINT, \
        end_node BIGINT,ref_lids CHARACTER VARYING,ordering CHARACTER VARYING, \
        speed NUMERIC, lanes BIGINT, fcn_class BIGINT, internal CHARACTER VARYING)")

    start = genonenode(start_zone)
    end = genonenode(end_zone)

    #print("Start node is: "+str(start)+" End node is: "+str(end))

    db.exec_("DROP TABLE if exists temp_table1")
    # Route 1
    db.exec_("SELECT * INTO temp_table1 from pgr_dijkstra('SELECT lid AS id, start_node AS source, end_node AS target, \
     link_cost AS cost, 1000 AS reverse_cost FROM cost_table'," + str(start) + "," + str(end) + ") \
     INNER JOIN cost_table ON(edge = lid)")


    # Result table creating
    db.exec_("DROP TABLE if exists result_table")
    db.exec_("SELECT " + str(start_zone) + " AS start_zone, " + str(end_zone) + " AS end_zone, 1 AS did,* INTO \
    result_table FROM temp_table1")

    # Getting total cost for route 1 and setting first stop criterion.
    cost_q = db.exec_("SELECT sum(link_cost) FROM temp_table1")
    cost_q.next()
    route1_cost = cost_q.value(0)
    print("Current cost route 1: " + str(route1_cost))
    route_stop = route1_cost

    # # Pen cost as breaking if stuck instead of nr_routes
    # pen_q = db.exec_("SELECT SUM(cost) from temp_table1")
    # pen_q.next()
    # # print("Pencost för rutt: "+str(pen_q.value(0)))
    # pen_stop = pen_q.value(0)

    # Calculationg alternative routes
    i = 2
    nr_routes = 1

    # while comp(route_stop, route1_cost, threshold):
    while True:
        if nr_routes >= 50:
            print("Warning: The number of routes was over 10 for start zone: \
             " + str(start_zone) + " and end zone: " + str(end_zone))
            break

        # Calculating penalizing term (P. 14 in thesis work)
        # Delta value
        delta_query = db.exec_("Select COUNT(*) from result_table")
        delta_query.next()
        delta = delta_query.value(0)
        #print("DELTA VALUE IS =:"+str(delta))
        # Parameter

        # Route 2
        db.exec_("DROP TABLE if exists temp_table2")
        db.exec_("SELECT * INTO temp_table2 FROM pgr_dijkstra('SELECT id, source, target, \
        CASE WHEN pen.cost IS NULL THEN subq.cost ELSE pen.cost END AS cost, reverse_cost \
        FROM (SELECT lid AS id, start_node AS source, end_node AS target, link_cost AS cost, 1000 AS reverse_cost \
        FROM cost_table) AS subq LEFT JOIN \
            (select lid as edge, max(cost) + (max(cost)/(" + str(my) + " * "+str(route_stop)+"))*LN(" + str(delta) + ") AS cost \
        from result_table group by lid ) AS pen ON \
        (subq.id = pen.edge)'," + str(start) + "," + str(end) + ") INNER JOIN cost_table ON(edge = lid)")

        # Saving route cost without penalty and updating route_stop.
        cost_q = db.exec_("SELECT SUM(cost_table.link_cost) AS tot_cost FROM temp_table2 \
        INNER JOIN cost_table ON cost_table.lid = temp_table2.lid;")
        cost_q.next()
        route_stop = cost_q.value(0)

        #print("Current cost route " + str(i) + ": " + str(route_stop))

        # print("difference is = " + str(route_stop / route1_cost))

        # Saving route cost with penalty. Remove comment if  penalty want to be used as breaking criterion
        # pen_q = db.exec_("SELECT SUM(cost) from temp_table2")
        # pen_q.next()
        # # print("Pencost för rutt: "+str(pen_q.value(0)))
        # pen_stop = pen_q.value(0)

        if comp(route_stop, route1_cost, threshold):
            db.exec_("INSERT INTO result_table SELECT " + str(start_zone) + " AS start_zone, " + str(
                end_zone) + " AS end_zone, " + str(
                i) + " AS did,*  FROM temp_table2")
            # Coverage calculation here.
            testa = db.exec_("SELECT sum(st_length(geom)) / (SELECT sum(st_length(geom)) FROM result_table WHERE did="+str(i)+") AS per \
            FROM (SELECT did,lid,geom FROM result_table WHERE did="+str(i)+" and lid = ANY(SELECT lid FROM result_table \
            WHERE NOT did >= "+str(i)+") group by lid,did,geom) as foo")
            testa.next()
            #print("rutt " + str(i) + " " + str(testa.value(0)) + " länk-km överlappar!")

            db.exec_("DROP TABLE if exists temp_table1")
            db.exec_("SELECT * INTO temp_table1 from temp_table2")
            i = i + 1
            nr_routes = nr_routes + 1
        else:
            break

    db.exec_("INSERT INTO all_results SELECT * FROM result_table")
    #print("all results inserted")
    return nr_routes


# Generates result table for selected OD-pairs
def selectedODResultTable(start_list, end_list, my, threshold, removed_lid):
    nr_routes = []
    db.exec_("DROP TABLE if exists all_results")
    db.exec_("CREATE TABLE all_results(start_zone INT, end_zone INT,did INT, seq INT, path_seq INT, \
    node BIGINT,edge BIGINT,cost DOUBLE PRECISION,agg_cost DOUBLE PRECISION, \
    link_cost DOUBLE PRECISION, id INT, geom GEOMETRY, lid BIGINT, start_node BIGINT, \
    end_node BIGINT,ref_lids CHARACTER VARYING,ordering CHARACTER VARYING, \
    speed NUMERIC, lanes BIGINT, fcn_class BIGINT, internal CHARACTER VARYING)")

    for x in range(len(end_list)):
        #print("Generating start zone = " + str(start_list[x]) + " end zone= " + str(end_list[x]))

        nr_routes.append(routeSetGeneration(start_list[x], end_list[x], my, threshold))

    # Creates new visualisation layer for selected pairs
    print_selected_pairs(start_list, end_list, removed_lid)


# Generates all to all result table
def allToAllResultTable(list, my, threshold):
    nr_routes = []
    db.exec_("DROP TABLE if exists all_results")
    db.exec_("CREATE TABLE all_results(start_zone INT, end_zone INT,did INT, seq INT, path_seq INT, \
    node BIGINT,edge BIGINT,cost DOUBLE PRECISION,agg_cost DOUBLE PRECISION, \
    link_cost DOUBLE PRECISION, id INT, geom GEOMETRY, lid BIGINT, start_node BIGINT, \
    end_node BIGINT,ref_lids CHARACTER VARYING,ordering CHARACTER VARYING, \
    speed NUMERIC, lanes BIGINT, fcn_class BIGINT, internal CHARACTER VARYING)")

    for y in range(len(list)):
        for x in range(len(list)):
            # From and to same zone is not interesting
            if y != x:
                nr_routes.append(routeSetGeneration(list[y], list[x], my, threshold))
        progress = y/len(list)
        #print("Patience! This is difficult, you know...  Progress:" + str(progress) + "%")


# Prints a route set based on whats in result_table.
def printRoutes(nr_routes):
    i = 1
    while i <= nr_routes:
        sqlcall = "(SELECT * FROM result_table WHERE did=" + str(i) + ")"
        uri.setDataSource("", sqlcall, "geom", "", "lid")
        layert = QgsVectorLayer(uri.uri(), " route " + str(i), "postgres")
        QgsProject.instance().addMapLayer(layert)
        i = i + 1


# od_effect (start zone,end zone,LID of the removed link)
# Function returns proportion of extra cost of alternative route in relation to opt route
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
                      " start_zone = "+str(start_zone)+" AND end_zone = "+str(end_zone)+" AND "
                    " did NOT IN (select did from all_results where start_zone = "+str(start_zone)+" AND end_zone = "+str(end_zone)+" AND  "+ removed_lid_string+ ")")

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
        return (float(cost_alt) / float(cost_opt))


# Returns [#non affected zones, #no routes in OD-pair, #all routes affected, mean_impairment, #pairs]
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
            mean_detour = sum_detour/count_detour
        else:
            mean_detour = -1
    return [count3,count2,count1, mean_detour, i-1]


# Print route analysis for selected OD-pairs (no duplicate zones allowed)
def print_selected_pairs(start_list, end_list, lids):
    # Removes layers not specified in removeRoutesLayers
    removeRoutesLayers()

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
        #print("Result of " + str(i) + " is: " + str(result_test))
        db.exec_(
            "UPDATE emme_results SET alt_route_cost = " + str(result_test) + " WHERE id = '" + str(start_list[i]) + "'"
                                                                                                                    " OR id = '" + str(
                end_list[i]) + "';")

        i += 1

    db.exec_("ALTER TABLE OD_lines ADD COLUMN id SERIAL PRIMARY KEY;")

    sqlcall = "(SELECT * FROM emme_results)"
    uri.setDataSource("", sqlcall, "geom", "", "id")
    layer = QgsVectorLayer(uri.uri(), "result_impairment ", "postgres")
    QgsProject.instance().addMapLayer(layer)

    values = (
        ('Not affected', -3, -3, QColor.fromRgb(153, 204, 255)),
        ('No route', -2, -2, QColor.fromRgb(0, 225, 200)),
        ('No route that is not affected', -1, -1, QColor.fromRgb(255, 0, 0)),
        ('Not searched', 0, 0, QColor.fromRgb(255, 255, 255)),
        ('Alternative route: 1-10 % impairment', 0, 1.1, QColor.fromRgb(102, 255, 102)),
        ('Alternative route: 10-100 % impairment', 1.1, 1000, QColor.fromRgb(255, 255, 0)),
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


# Get a list with node_nr and zone_id.
def getAllNodes():
    db.exec_("CREATE TABLE IF NOT EXISTS od_lid AS (SELECT * FROM(SELECT ROW_NUMBER() OVER (PARTITION BY id \
                   ORDER BY id, distance) AS score, id, lid, start_node, distance \
                   FROM(SELECT emme.id, lid, start_node, ST_distance(geom, emme_centroid) AS \
                   distance FROM model_graph, (SELECT id, ST_centroid(geom) AS \
                   emme_centroid, geom AS emme_geom FROM emme_zones WHERE id > 0) AS emme \
                   WHERE ST_Intersects(geom, emme_geom) ORDER BY distance) AS subq) AS subq \
                   WHERE score = 1)")

    query = db.exec_("SELECT start_node, id FROM od_lid")
    node_list = []
    # Saving SQL answer into matrix
    while query.next():
        node_list.append(query.value(1))

    return (node_list)


# Generate shortest path between one_node to all the other
def onetoMany(one_node):
    print("one to many")

    db.exec_("DROP TABLE if exists dijk_test")
    db.exec_("SELECT * INTO dijk_test FROM pgr_Dijkstra('SELECT lid AS id, start_node AS source, \
    end_node AS target, ST_length(geom)/speed*3.6 AS cost, 100000 AS reverse_cost \
    FROM model_graph'," + str(one_node) + ", ARRAY(SELECT start_node FROM od_lid WHERE NOT \
    (start_node='" + str(one_node) + "'))) INNER JOIN cost_table ON(edge = lid) ")

# Analysing all-to-all result for list and removed lid  # CANT decide where this should go either gis_layer or python.
def allToAll(list, removed_lids):
    #Removes layers not specified in removeRoutesLayers
    removeRoutesLayers()

    removed_lid_string = "( lid = " + str(removed_lids[0])
    i=1
    while i < len(removed_lids):
        removed_lid_string += " or lid =" + str(removed_lids[i])
        i +=1
    removed_lid_string += ")"

    # Queryn skapar tabell för alla länkar som går igenom removed_lid
    db.exec_("DROP TABLE IF EXIST temp_test")
    db.exec_(
        " select * into temp_test from all_results f where exists(select 1 from all_results l where " + removed_lid_string + " and"
                                 " (f.start_zone = l.start_zone and f.end_zone = l.end_zone and f.did = l.did))")

    # Här vill jag skapa nytt lager som visar intressanta saker för varje zon
    # Create emme_result table
    db.exec_("DROP table if exists emme_results")
    db.exec_("SELECT 0 as nr_non_affected, 0 as nr_no_routes, 0 as nr_all_routes_affected, 0.0 as mean_impairment, 0 as nr_pairs,* INTO emme_results FROM emme_zones")

    i = 0
    while i < len(list):
        result = analysis_multiple_zones(list[i], list, removed_lids)
        db.exec_("UPDATE emme_results SET nr_non_affected = " + str(result[0]) +" , nr_no_routes = " +
                str(result[1]) + " , nr_all_routes_affected = " +  str(result[2]) +" , mean_impairment = " +
                str(result[3]) + " , nr_pairs = " +  str(result[4]) + " WHERE id = "+
                str(list[i] ) + ";")
        i +=1

    ############################ Create layer for mean impairment
    sqlcall = "(SELECT * FROM emme_results)"
    uri.setDataSource("", sqlcall, "geom", "", "id")

    layer = QgsVectorLayer(uri.uri(), "mean_impairment ", "postgres")
    QgsProject.instance().addMapLayer(layer)

    values = (
        ('Not searched', 0, 0, QColor.fromRgb(255, 255, 255)),
        ('No impairment', -1, -1, QColor.fromRgb(153, 204, 255)),
        ('Mean impairment 1-20% ', 0, 1.2, QColor.fromRgb(102, 255, 102)),
        ('Mean impairment 20-30% ', 1.2, 1.3, QColor.fromRgb(255, 255, 153)),
        ('Mean impairment 30-50% ', 1.3, 1.5, QColor.fromRgb(255, 178, 102)),
        ('Mean impairment 50-100% ', 1.5, 100, QColor.fromRgb(255, 102, 102)),
    )

    # create a category for each item in values
    ranges = []
    for label, lower, upper, color in values:
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        symbol.setColor(QColor(color))
        rng = QgsRendererRange(lower, upper, symbol, label)
        ranges.append(rng)

    ## create the renderer and assign it to a layer
    expression = 'mean_impairment'  # field name
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

def allToAllBigTest(list,removed_lids):
    #Removes layers not specified in removeRoutesLayers
    removeRoutesLayers()

    removed_lid_string = "( lid = " + str(removed_lids[0])
    i=1
    while i < len(removed_lids):
        removed_lid_string += " or lid =" + str(removed_lids[i])
        i +=1
    removed_lid_string += ")"

    # Queryn skapar tabell för alla länkar som går igenom removed_lid
    db.exec_("DROP TABLE IF EXIST temp_test")
    db.exec_(
        " select * into temp_test from dijk_all_results_mini f where exists(select 1 from dijk_all_results_mini l where " + removed_lid_string + " and"
                                                                                                                             " (f.start_zone = l.start_zone and f.end_zone = l.end_zone and f.did = l.did))")

    # Här vill jag skapa nytt lager som visar intressanta saker för varje zon
    # Create emme_result table
    db.exec_("DROP table if exists emme_results")
    db.exec_("SELECT 0 as nr_non_affected, 0 as nr_no_routes, 0 as nr_all_routes_affected, 0.0 as mean_impairment, 0 as nr_pairs,* INTO emme_results FROM emme_zones")


    i = 0
    while i < len(list):
        result = analysis_multiple_zones(list[i], list, removed_lids)
        db.exec_("UPDATE emme_results SET nr_non_affected = " + str(result[0]) +" , nr_no_routes = " +
                str(result[1]) + " , nr_all_routes_affected = " +  str(result[2]) +" , mean_impairment = " +
                str(result[3]) + " , nr_pairs = " +  str(result[4]) + " WHERE id = "+
                str(list[i] ) + ";")
        i +=1


    # Create layer for mean impairment
    sqlcall = "(SELECT * FROM emme_results)"
    uri.setDataSource("", sqlcall, "geom", "", "id")

    layer = QgsVectorLayer(uri.uri(), "mean_impairment ", "postgres")
    QgsProject.instance().addMapLayer(layer)

    values = (
        ('Not searched', 0, 0, QColor.fromRgb(255, 255, 255)),
        ('No impairment', -1, -1, QColor.fromRgb(153, 204, 255)),
        ('Mean impairment 1-20% ', 0, 1.2, QColor.fromRgb(102, 255, 102)),
        ('Mean impairment 20-30% ', 1.2, 1.3, QColor.fromRgb(255, 255, 153)),
        ('Mean impairment 30-50% ', 1.3, 1.5, QColor.fromRgb(255, 178, 102)),
        ('Mean impairment 50-100% ', 1.5, 100, QColor.fromRgb(255, 102, 102)),
    )

    # create a category for each item in values
    ranges = []
    for label, lower, upper, color in values:
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        symbol.setColor(QColor(color))
        rng = QgsRendererRange(lower, upper, symbol, label)
        ranges.append(rng)

    ## create the renderer and assign it to a layer
    expression = 'mean_impairment'  # field name
    layer.setRenderer(QgsGraduatedSymbolRenderer(expression, ranges))

    # Create layer for nr_affected OD-pairs
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


    ############################ Create OD-lines between all afected OD-pairs

    db.exec_("drop table if exists temp_od_lines")
    db.exec_("SELECT all_results.start_zone, all_results.end_zone, geom as start_geom "
             "into temp_od_lines from emme_zones join(SELECT start_zone, end_zone from all_results f "
             "where exists(select 1 from all_results l where "+removed_lid_string+" and (f.start_zone = l.start_zone "
             "and f.end_zone = l.end_zone and f.did = l.did)) and did = 1 group by start_zone, end_zone) as all_results "
             " ON all_results.start_zone = emme_zones.id")

    db.exec_("drop table if exists all_to_all_od_lines")
    db.exec_("select temp_od_lines.start_zone, temp_od_lines.end_zone, temp_od_lines.start_geom  "
             ", emme_zones.geom as end_geom,ST_MakeLine(ST_Centroid(start_geom), ST_Centroid(emme_zones.geom)) "
             "as geom into all_to_all_od_lines from temp_od_lines join emme_zones on temp_od_lines.end_zone = emme_zones.id")
    db.exec_("ALTER TABLE all_to_all_od_lines ADD COLUMN id SERIAL PRIMARY KEY;")

    sqlcall = "(select * from all_to_all_od_lines)"

    uri.setDataSource("", sqlcall, "geom", "", "id")
    layer = QgsVectorLayer(uri.uri(), " all_to_all_od_lines", "postgres")
    QgsProject.instance().addMapLayer(layer)

    ############################ All affected routes (tree)
    db.exec_("drop table if exists temp_affected_links")
    db.exec_("CREATE TABLE temp_affected_links (ID int NOT NULL PRIMARY KEY, geom geometry NOT NULL, count bigint);")
    db.exec_("insert into temp_affected_links select id, geom, count(id)  from all_results f where  exists ("
             "select 1 from all_results l where "+removed_lid_string+" and (f.start_zone = l.start_zone "
             "and f.end_zone = l.end_zone and f.did = l.did)) and did = 1 GROUP by id,geom")

    sqlcall = "(select * from temp_affected_links)"

    uri.setDataSource("", sqlcall, "geom", "", "id")
    layer = QgsVectorLayer(uri.uri(), " affected_links", "postgres")
    QgsProject.instance().addMapLayer(layer)

# Generate route set using one to many with penalty currently not working correctly
def onetoManyPenalty(one_node, many_nodes_list, my):
    print("one to many with penalty")

    print(str(one_node) + "  " + str(many_nodes_list))

    # Route 1
    db.exec_("DROP TABLE if exists dijk_temp_table1")
    db.exec_("SELECT " + str(one_node) + " AS one_node,* INTO dijk_temp_table1 FROM pgr_Dijkstra('SELECT lid AS id, start_node AS source, \
        end_node AS target, ST_length(geom)/speed*3.6 AS cost, 100000 AS reverse_cost \
        FROM model_graph'," + str(one_node) + ", ARRAY(SELECT start_node FROM od_lid \
        WHERE start_node='" + str(many_nodes_list[0]) + "' or start_node='" + str(many_nodes_list[1]) + "' or \
        start_node='" + str(many_nodes_list[2]) + "') ) \
        INNER JOIN cost_table ON(edge = lid) ")

    db.exec_("DROP TABLE if exists dijk_result_table")
    db.exec_("SELECT 0 as delta, 1 AS did,* INTO \
        dijk_result_table FROM dijk_temp_table1")
    print("Route 1 inserted into dijk_result table!!")
    # Route 1 FINISHED

    # Route 2-X
    i = 2

    nr_routes = 1
    while i < 5:

        # Calculate delta an insert into the right penalty.
        for x in many_nodes_list:
            delta_query = db.exec_("Select COUNT(*) from dijk_result_table WHERE one_node ='" + str(one_node)
                                   + "' and end_vid='" + str(x) + "'")
            delta_query.next()
            delta = delta_query.value(0)
            print("delta value for " + str(x) + " is " + str(delta))
            db.exec_("UPDATE dijk_result_table SET delta =" + str(delta) + " WHERE one_node='" + str(one_node)
                     + "' and end_vid='" + str(x) + "' and did = "+str(i-1)+"")

        db.exec_("DROP TABLE if exists dijk_temp_table2")
        db.exec_("SELECT " + str(one_node) + " AS one_node,* INTO dijk_temp_table2 \
        FROM pgr_dijkstra('SELECT id, source, target, CASE WHEN pen.cost IS NULL THEN subq.cost \
        ELSE pen.cost END AS cost, reverse_cost FROM (SELECT lid AS id, start_node AS source, \
        end_node AS target, link_cost AS cost, 100000 AS reverse_cost FROM cost_table) AS subq LEFT JOIN \
        (select lid as edge, max(cost) + (max(cost)/(" + str(my) + " * min(cost)))*LN(delta) AS cost \
        from dijk_result_table group by lid, end_vid, delta) AS pen ON \
        (subq.id = pen.edge)'," + str(one_node) + ", ARRAY(SELECT start_node FROM od_lid \
        WHERE start_node='" + str(many_nodes_list[0]) + "' or start_node='" + str(many_nodes_list[1]) + "' or \
        start_node='" + str(many_nodes_list[2]) + "') ) INNER JOIN cost_table ON(edge = lid)")

        db.exec_("INSERT INTO dijk_result_table SELECT 0 AS delta, " + str(i) + " AS did,*  FROM dijk_temp_table2")
        print("Route " + str(i) + " inserted into dijk_result table!!")
        db.exec_("DROP TABLE if exists dijk_temp_table1")
        db.exec_("SELECT * INTO dijk_temp_table1 from dijk_temp_table2")
        i = i + 1
        nr_routes = nr_routes + 1

#Similar to routeSetGeneration, reuturns overlap
def overlapDifferentMy(start_zone, end_zone, my, threshold):

    db.exec_("CREATE TABLE IF NOT EXISTS cost_table AS (select ST_Length(geom)/speed*3.6 AS link_cost, * \
        from model_graph)")
    db.exec_("CREATE TABLE IF NOT EXISTS all_results(start_zone INT, end_zone INT,did INT, seq INT, path_seq INT, \
            node BIGINT,edge BIGINT,cost DOUBLE PRECISION,agg_cost DOUBLE PRECISION, \
            link_cost DOUBLE PRECISION, id INT, geom GEOMETRY, lid BIGINT, start_node BIGINT, \
            end_node BIGINT,ref_lids CHARACTER VARYING,ordering CHARACTER VARYING, \
            speed NUMERIC, lanes BIGINT, fcn_class BIGINT, internal CHARACTER VARYING)")

    db.exec_("CREATE TABLE IF NOT EXISTS all_results(start_zone INT, end_zone INT,did INT, seq INT, path_seq INT, \
            node BIGINT,edge BIGINT,cost DOUBLE PRECISION,agg_cost DOUBLE PRECISION, \
            link_cost DOUBLE PRECISION, id INT, geom GEOMETRY, lid BIGINT, start_node BIGINT, \
            end_node BIGINT,ref_lids CHARACTER VARYING,ordering CHARACTER VARYING, \
            speed NUMERIC, lanes BIGINT, fcn_class BIGINT, internal CHARACTER VARYING)")

    start = genonenode(start_zone)
    end = genonenode(end_zone)

    # print("Start node is: "+str(start)+" End node is: "+str(end))

    db.exec_("DROP TABLE if exists temp_table1")
    # Route 1
    db.exec_("SELECT * INTO temp_table1 from pgr_dijkstra('SELECT lid AS id, start_node AS source, end_node AS target, \
         link_cost AS cost, 1000 AS reverse_cost FROM cost_table'," + str(start) + "," + str(end) + ") \
         INNER JOIN cost_table ON(edge = lid)")

    # Result table creating
    db.exec_("DROP TABLE if exists result_table")
    db.exec_("SELECT " + str(start_zone) + " AS start_zone, " + str(end_zone) + " AS end_zone, 1 AS did,* INTO \
        result_table FROM temp_table1")

    # Getting total cost for route 1 and setting first stop criterion.
    cost_q = db.exec_("SELECT sum(link_cost) FROM temp_table1")
    cost_q.next()
    route1_cost = cost_q.value(0)
    # print("Current cost route 1: " + str(route1_cost))
    route_stop = route1_cost

    # # Pen cost as breaking if stuck instead of nr_routes
    # pen_q = db.exec_("SELECT SUM(cost) from temp_table1")
    # pen_q.next()
    # # print("Pencost för rutt: "+str(pen_q.value(0)))
    # pen_stop = pen_q.value(0)

    # Calculationg alternative routes
    i = 2
    nr_routes = 1
    sum_overlap = 0
    # while comp(route_stop, route1_cost, threshold):
    while True:
        if nr_routes >= 50:
            print("Warning: The number of routes was over 10 for start zone: \
                 " + str(start_zone) + " and end zone: " + str(end_zone))
            break

        # Calculating penalizing term (P. 14 in thesis work)
        # Delta value
        delta_query = db.exec_("Select COUNT(*) from result_table")
        delta_query.next()
        delta = delta_query.value(0)
        # print("DELTA VALUE IS =:"+str(delta))
        # Parameter

        # Route 2
        db.exec_("DROP TABLE if exists temp_table2")
        db.exec_("SELECT * INTO temp_table2 FROM pgr_dijkstra('SELECT id, source, target, \
            CASE WHEN pen.cost IS NULL THEN subq.cost ELSE pen.cost END AS cost, reverse_cost \
            FROM (SELECT lid AS id, start_node AS source, end_node AS target, link_cost AS cost, 1000 AS reverse_cost \
            FROM cost_table) AS subq LEFT JOIN \
                (select lid as edge, max(cost) + (max(cost)/(" + str(my) + " * "+str(route_stop)+"))*LN(" + str(delta) + ") AS cost \
            from result_table group by lid ) AS pen ON \
            (subq.id = pen.edge)'," + str(start) + "," + str(end) + ") INNER JOIN cost_table ON(edge = lid)")

        # Saving route cost without penalty and updating route_stop.
        cost_q = db.exec_("SELECT SUM(cost_table.link_cost) AS tot_cost FROM temp_table2 \
            INNER JOIN cost_table ON cost_table.lid = temp_table2.lid;")
        cost_q.next()
        route_stop = cost_q.value(0)
        # print("Current cost route " + str(i) + ": " + str(cost_q.value(0)))

        # print("difference is = " + str(route_stop / route1_cost))

        # Saving route cost with penalty. Remove comment if  penalty want to be used as breaking criterion
        # pen_q = db.exec_("SELECT SUM(cost) from temp_table2")
        # pen_q.next()
        # # print("Pencost för rutt: "+str(pen_q.value(0)))
        # pen_stop = pen_q.value(0)

        if comp(route_stop, route1_cost, threshold):
            db.exec_("INSERT INTO result_table SELECT " + str(start_zone) + " AS start_zone, " + str(
                end_zone) + " AS end_zone, " + str(
                i) + " AS did,*  FROM temp_table2")
            # Coverage calculation here.
            testa = db.exec_(
                "SELECT sum(st_length(geom)) / (SELECT sum(st_length(geom)) FROM result_table WHERE did=" + str(i) + ") AS per \
                FROM (SELECT did,lid,geom FROM result_table WHERE did=" + str(i) + " and lid = ANY(SELECT lid FROM result_table \
                WHERE NOT did >= " + str(i) + ") group by lid,did,geom) as foo")
            testa.next()
            #print("rutt " + str(i) + " " + str(testa.value(0)) + " länk-km överlappar!")

            db.exec_("DROP TABLE if exists temp_table1")
            db.exec_("SELECT * INTO temp_table1 from temp_table2")
            i = i + 1
            nr_routes = nr_routes + 1
        else:
            break
        if testa.value(0):
            sum_overlap += testa.value(0)

    db.exec_("INSERT INTO all_results SELECT * FROM result_table")
    # print("all results inserted")
    if nr_routes > 1:
        return sum_overlap/(nr_routes-1)
    else:
        return 0

def excelStats(start_list,end_list,my_list,threshold):
    db.exec_("DROP TABLE if exists all_results")
    #Overlap
    j = 0
    while j < len(my_list):
        tic()
        i = 0
        sum_overlap = 0
        while i < len(start_list):
            # print("i är : " + str(i))
            sum_overlap += overlapDifferentMy(start_list[i], end_list[i], my_list[j], threshold)
            # print(str(sum_overlap))
            i += 1
        print("my är: " + str(my_list[j]) +  " med overlap: " + str(sum_overlap / i))
        j += 1
        toc()
    db.exec_("DROP TABLE if exists all_results")

    # Nr routes
    j = 0
    while j < len(my_list):
        i = 0
        sum_nr_routes = 0
        while i < len(start_list):
            # print("i är : " + str(i))
            sum_nr_routes += routeSetGeneration(start_list[i], end_list[i], my_list[j], threshold)
            # print(str(sum_overlap))
            i += 1
        print("my är: " + str(my_list[j]) + " med avg nr routes: " + str(sum_nr_routes / i))
        j += 1


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
    removeRoutesLayers()

    if db.isValid():
        # Variable definitions
        my = 0.01
        threshold = 1.25
        # ___________________________________________________________________________________________________________________

        # __________________________________________________________________________________________________________________

        #Start generating several route sets

        # List of OD-pairs

        #Används för selected_routes (rutter OD-par runt city)
        start_list = [6904, 6884, 6869, 6887, 6954, 7317, 7304, 7541]
        end_list = [6837, 6776, 7642, 7630, 7878, 6953, 7182, 7609]

        # Korta OD-par
        # start_list = [7143, 7603, 7412, 6904, 6970, 7190, 6893, 7551, 7894, 7852, 7223, 7328, 7648]
        # end_list = [6820, 7585, 7635, 6870, 6937, 7170, 7161, 7539, 7886, 7946, 6973, 7308, 7661]

        # Långa OD-par
        start_list = [7472, 7815,7128,7801,7707,7509,7304,7151,7487,7737]
        end_list = [7556,7635,6912,7603, 6976, 7174,7680,7053,7282,6822]

        # Nya Långa OD-par
        # start_list = [7487, 7166,7721,7302]
        # end_list = [7282, 7506,7817,7782]


        list = [8005, 7195,6884, 6837, 6776, 7835, 7864, 6955,7570,7422,7680,7557,7560,6879,6816, 7630,7162,7187,7227]
        #list = [6904, 6884, 6837, 6776, 7835]

        removed_lid = 89227  # Götgatan
        removed_lid = [830259]  # Söderledstunneln


        # [81488, 83171] för Essingeleden
        # [83025, 84145] för Söderleden
        removed_lids = [83025, 84145]
        #selectedODResultTable(start_list, end_list,my,threshold,removed_lid)

        # allToAllResultTable(list,my,threshold)
        # allToAll(list, removed_lids)
        #___________________________________________________________________________________________________________________
        db.exec_("DROP TABLE if exists all_results")
        db.exec_("DROP TABLE if exists cost_table")


        my_list = [0.01, 0.05, 0.2, 0.4, 0.6, 0.8, 1.0, 1.4, 1.8, 2.2, 3, 5, 10]
        my_list = [0.001, 0.003,0.005, 0.01, 0.02, 0.03,0.05]
        #my_list = [0.05]

        #selectedODResultTable(start_list, end_list,my,threshold,removed_lids)
        #excelStats(start_list, end_list, my_list,threshold)
        # allToAllResultTable(list,my,threshold)
        # allToAll(list, removed_lids)

        start_zone = 7487
        end_zone = 7282


        #nr_routes = routeSetGeneration(start_zone, end_zone, my, threshold)
        # printRoutes(nr_routes)


        # ___________________________________________________________________________________________________________________

        # Generating all to all OBSERVERA TAR ca 1h att köra
        # LAZY SOLUTION RIGHT HERE with table creating and deleting.
        # db.exec_("DROP TABLE if exists dijk_all_results_mini")
        # db.exec_("SELECT 12345 AS one_node,* INTO dijk_all_results_mini FROM pgr_Dijkstra('SELECT lid AS id, start_node AS source, \
        #          end_node AS target, ST_length(geom)/speed*3.6 AS cost, 100000 AS reverse_cost \
        #          FROM model_graph', 43912, \
        #          ARRAY(SELECT start_node FROM od_lid WHERE NOT start_node='43838')) \
        #          INNER JOIN cost_table ON(edge = lid) ")
        # #db.exec_("ALTER TABLE dijk_all_results_mini ADD one_node")
        #
        # db.exec_("DELETE FROM dijk_all_results_mini")
        #
        # node_list = getAllNodes()
        # print("storlek på lista"+str(len(node_list))+" något värde"+str(node_list[2]))
        # for x in node_list:
        #     onetoMany(x)
        # for x in range(10):
        # onetoMany(node_list[x])
        #  print("nodes sent in: "+str(node_list[x]))

        # Testar one to many with penalty
        # end_list = [genonenode(6837), genonenode(6776), genonenode(7553)]
        # start_zone = genonenode(6904)
        #
        # onetoManyPenalty(start_zone, end_list, my)
        # removed_lids = [89227]
        # listan = getAllNodes()
        #print("lsitan är:"+ str(listan))
        # allToAllBigTest(listan, removed_lids)

        toc();


if __name__ == "__main__" or __name__ == "__console__":
    main()

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
            layer.name()) != "Centroider" and str(layer.name()) != "dijk_result_table" and str(layer.name()) != "ata_lid"\
                and str(layer.name()) != "Link used by 3 shortest paths" and str(layer.name()) != "Link used by 0 shortest paths"\
                and str(layer.name()) != "OD_pairs":
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

# Returns [#non affected zones, #no routes in OD-pair, #all routes affected, mean_deterioration, #pairs]
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
    db.exec_("SELECT 0 as nr_non_affected, 0 as nr_no_routes, 0 as nr_all_routes_affected, 0.0 as mean_deterioration, 0 as nr_pairs,* INTO emme_results FROM emme_zones")

    i = 0
    while i < len(list):
        result = analysis_multiple_zones(list[i], list, removed_lids)
        db.exec_("UPDATE emme_results SET nr_non_affected = " + str(result[0]) +" , nr_no_routes = " +
                str(result[1]) + " , nr_all_routes_affected = " +  str(result[2]) +" , mean_deterioration = " +
                str(result[3]) + " , nr_pairs = " +  str(result[4]) + " WHERE id = "+
                str(list[i] ) + ";")
        i +=1

    ############################ Create layer for mean deterioration
    sqlcall = "(SELECT * FROM emme_results)"
    uri.setDataSource("", sqlcall, "geom", "", "id")

    layer = QgsVectorLayer(uri.uri(), "mean_deterioration ", "postgres")
    QgsProject.instance().addMapLayer(layer)

    values = (
        ('Not searched', 0, 0, QColor.fromRgb(255, 255, 255)),
        ('No deterioration', -1, -1, QColor.fromRgb(153, 204, 255)),
        ('Mean deterioration 1-10% ', 0, 1.1, QColor.fromRgb(102, 255, 102)),
        ('Mean deterioration 10-20% ', 1.1, 1.2, QColor.fromRgb(255, 255, 153)),
        ('Mean deterioration 20-30% ', 1.2, 1.3, QColor.fromRgb(255, 178, 102)),
        ('Mean deterioration 30-100% ', 1.3, 100, QColor.fromRgb(255, 102, 102)),
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

# DATABASE CONNECTION ------------------------------------------------------
uri = QgsDataSourceUri()
# set host name, port, database name, username and password

#Mattias o GUstavs
#uri.setConnection("localhost", "5432", "exjobb", "postgres", "password123")

#TP4030
uri.setConnection("localhost", "5455", "mattugusna", "mattugusna", "password123")

print(uri.uri())
db = QSqlDatabase.addDatabase('QPSQL')

print("HEJ")
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

        # db.exec_("DROP TABLE if exists all_results")
        # db.exec_("DROP TABLE if exists cost_table")

        list = [7877,7630, 6837, 6877,6884, 6922, 6904, 6968]
        removed_lids = [83025, 84145]
        print("HEJ2")
        #allToAllResultTable(list,my,threshold)
        #allToAll(list, removed_lids)

        od_res = db.exec_("SELECT start_zone,end_zone FROM remote_results group by start_zone, end_zone limit 10")
        od_res.next()
        route1_cost = od_res.value(0)
        print("Current cost route 1: " + str(route1_cost))

        # Ladda listor med OD-par
        origin = []
        destination = []

        while od_res.next():
            origin.append(od_res.value(0))
            destination.append(od_res.value(1))
            #print("Origin: " + str(origin))
            #print("Dest: " + str(destination))

        #allToAll(list, removed_lids)



        toc();


if __name__ == "__main__" or __name__ == "__console__":
    main()

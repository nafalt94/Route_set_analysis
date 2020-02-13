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
                and str(layer.name()) != "OpenStreetMap" and str(layer.name()) != "all_results" and str(layer.name()) != "Centroider" and str(layer.name()) != "dijk_result_table":
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
    #
    db.exec_("CREATE TABLE IF NOT EXISTS cost_table AS (select ST_Length(geom)/speed*3.6 AS link_cost, * \
    from model_graph)")

    node = genStartNode(start_zone, end_zone)
    start = node[0]
    end = node[1]
    print("Start zone is: "+str(start)+" End zone is: "+str(end))
    db.exec_("DROP TABLE if exists temp_table1")
    # Route 1
    db.exec_("SELECT * INTO temp_table1 from pgr_dijkstra('SELECT lid AS id, start_node AS source, end_node AS target, \
     link_cost AS cost, 3*link_cost AS reverse_cost FROM cost_table'," + str(start) + "," + str(end) + ") \
     INNER JOIN cost_table ON(edge = lid)")

    # Saving route 1 in query
    temp_q = db.exec_("SELECT * FROM temp_table1 ORDER BY path_seq")
    queries = []
    queries.append(temp_q)
    temp_q.next()
    print("Funkade databasen eller? :"+str(temp_q.value(0)))
    # Result table creating
    db.exec_("DROP TABLE if exists result_table")
    db.exec_("SELECT " + str(start_zone) + " AS start_zone, " + str(end_zone) + " AS end_zone, 1 AS did,* INTO \
    result_table FROM temp_table1")

    # Getting the agg. cost for best route
    cost_q = db.exec_("SELECT sum(link_cost) FROM temp_table1")

    cost_q.next()
    route1_cost = cost_q.value(0)
    print("Current cost route 1: " + str(route1_cost))
    route_stop = route1_cost

    pen_q = db.exec_("SELECT SUM(cost) from temp_table1")
    pen_q.next()
    #print("Pencost för rutt: "+str(pen_q.value(0)))
    pen_stop = pen_q.value(0)

    ## Calculationg alternative routes
    i = 2

    nr_routes = 1
    print(" Rätt värden? route_stop = "+str(route_stop) + " route1_cost = "+str(route1_cost) + " threshhold = "+str(threshold))
    while comp(route_stop, route1_cost, threshold):
        if pen_stop > 100000000:
            print("Warning: Pencost was over 1 billion")
            break
        # Calculating penalizing term (P. 14 in thesis work)
        # Delta value
        delta_query = db.exec_("Select COUNT(*) from result_table")
        delta_query.next()
        delta = delta_query.value(0)
        print("DELTA VALUE IS =:"+str(delta))
        # Parameter

        # Route 2
        db.exec_("DROP TABLE if exists temp_table2")
        db.exec_("SELECT * INTO temp_table2 FROM pgr_dijkstra('SELECT id, source, target, \
        CASE WHEN pen.cost IS NULL THEN subq.cost ELSE pen.cost END AS cost, reverse_cost \
        FROM (SELECT lid AS id, start_node AS source, end_node AS target, link_cost AS cost, 100000000 AS reverse_cost \
        FROM cost_table) AS subq LEFT JOIN \
            (select lid as edge, max(cost) + (max(cost)/("+str(my)+" * min(cost)))*LN("+str(delta)+") AS cost \
        from result_table group by lid ) AS pen ON \
        (subq.id = pen.edge)',"+str(start)+","+str(end)+") INNER JOIN cost_table ON(edge = lid)")

        # Saving route cost without penalty.
        temp_q = db.exec_("SELECT * FROM temp_table2 ORDER BY path_seq")
        queries.append(temp_q)
        cost_q = db.exec_("SELECT SUM(cost_table.link_cost) AS tot_cost FROM temp_table2 \
        INNER JOIN cost_table ON cost_table.lid = temp_table2.lid;")
        cost_q.next()
        #print("Current cost route " + str(i) + ": " + str(cost_q.value(0)))
        route_stop = cost_q.value(0)
        #print("difference is = " + str(route_stop / route1_cost))

        # Saving route cost with penalty.
        pen_q = db.exec_("SELECT SUM(cost) from temp_table2")
        pen_q.next()
        #print("Pencost för rutt: "+str(pen_q.value(0)))
        pen_stop = pen_q.value(0)

        if comp(route_stop, route1_cost, threshold):
            db.exec_("INSERT INTO result_table SELECT " + str(start_zone) + " AS start_zone, " + str(
                end_zone) + " AS end_zone, " + str(
                i) + " AS did,*  FROM temp_table2")

            db.exec_("DROP TABLE if exists temp_table1")
            db.exec_("SELECT * INTO temp_table1 from temp_table2")
            i = i + 1
            nr_routes = nr_routes + 1

    db.exec_("INSERT INTO all_results SELECT * FROM result_table")
    return nr_routes

# Prints a route set based on whats in result_table.
def printRoutes(nr_routes):
    i = 1
    while i <= nr_routes:
        sqlcall = "(SELECT * FROM result_table WHERE did=" + str(i) + ")"
        uri.setDataSource("", sqlcall, "geom", "", "lid")
        layert = QgsVectorLayer(uri.uri()," route " + str(i), "postgres")
        QgsProject.instance().addMapLayer(layert)
        i = i + 1

# od_effect (start zone,end zone,LID of the removed link)
# Function returns proportion of extra cost of alternative route in relation to opt route
def odEffect(start, end, lid):
    start_zone = start
    end_zone = end
    removed_lid = lid

    #Finding best, non-affected alternative route
    query1 = db.exec_("SELECT MIN(did) FROM all_results WHERE"
                      " start_zone = "+str(start_zone)+" AND end_zone = "+str(end_zone)+" AND "
                    " did NOT IN (select did from all_results where start_zone = "+str(start_zone)+" AND end_zone = "+str(end_zone)+" AND  lid = "+str(removed_lid)+")")
    query1.next()
    id_alt = str(query1.value(0))
    #print("id_alt är: "+ id_alt)

    if id_alt== "NULL":
        #Either there's only one route in the route set or the route set is empty
        query = db.exec_("SELECT MIN(did) FROM all_results where start_zone = "+str(start_zone)+" AND end_zone = "+str(end_zone)+"")
        query.next()

        if query.value(0) :
            #There is no route that is not affected
            return -1
        else:
            #There is no routes with that start and end zone
            return -2;

    elif  id_alt == "1":
        #print("Zon påverkas inte")
        return -3
    else:
        #print("Zon påverkas och bästa id är:" + id_alt)

        # Fetching cost of the optimal route and the alternative
        query2 = db.exec_("SELECT sum(link_cost) from all_results where "
                          " (start_zone = "+str(start_zone)+" AND end_zone = "+str(end_zone)+") AND "
                                        "(did = 1 OR did = "+str(id_alt)+") group by did")
        query2.next()
        # Best cost
        cost_opt = str(query2.value(0))

        # Alternative cost
        query2.next()
        cost_alt = str(query2.value(0))

        # Proportion of extra cost of alternative route in relation to opt route
        # print("cost_opt = " + cost_opt + " and cost_alt = " + cost_alt)
        return (float(cost_alt)/float(cost_opt))

#create_table creates neccessary tables for visualization of the OD-pairs in star_list and end_list
def create_tables(start_list, end_list,lid):
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
                 "AS geom FROM emme_zones where id = "+str(start_list[i])+" OR id = "+str(end_list[i])+"")

        result_test = odEffect(start_list[i], end_list[i], lid)
        print("Result of " + str(i) + " is: " + str(result_test))
        db.exec_(
            "UPDATE emme_results SET alt_route_cost = " + str(result_test) + " WHERE id = '" + str(start_list[i]) + "'"
                                                                                                                    " OR id = '" + str(
                end_list[i]) + "';")

        i = i + 1

    db.exec_("ALTER TABLE OD_lines ADD COLUMN id SERIAL PRIMARY KEY;")

# Returns [#non affected zones, #no routes in OD-pair, #all routes affected, mean_impairment, #pairs]
def many_zones(start_node, end_list,lid):

    count3 = 0
    count2 = 0
    count1 = 0
    count_detour = 0
    sum_detour = 0

    i = 0
    while i < len(end_list):
        result_test = odEffect(start_node, end_list[i], lid)

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

    mean_detour = sum_detour/count_detour
    return [count3,count2,count1, mean_detour, i]

# Print zones from emme_results
def print_zones():

    sqlcall = "(SELECT * FROM emme_results)"
    uri.setDataSource("", sqlcall, "geom", "", "id")
    layer = QgsVectorLayer(uri.uri(), "result_impairment " , "postgres")
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
        node_list.append(query.value(0))

    return(node_list)

# Generate routes between one_node to all the rest
def onetoMany(one_node):
    print("one to many")

    db.exec_("DROP TABLE if exists dijk_test")
    db.exec_("SELECT * INTO dijk_test FROM pgr_Dijkstra('SELECT lid AS id, start_node AS source, \
    end_node AS target, ST_length(geom)/speed*3.6 AS cost, 100000 AS reverse_cost \
    FROM model_graph'," + str(one_node) + ", ARRAY(SELECT start_node FROM od_lid WHERE NOT \
    (start_node='" + str(one_node) + "'))) INNER JOIN cost_table ON(edge = lid) ")



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
        my = 1
        threshold = 1.6
        #___________________________________________________________________________________________________________________
        # Generating "all" the route sets needed.
        # alla_od = db.exec_("SELECT id FROM emme_zones ORDER BY id")
        # id = []
        # while alla_od.next():
        #     id.append(alla_od.value(0))
        #
        # nr_routes = []
        # db.exec_("DROP TABLE if exists all_results")
        # db.exec_("CREATE TABLE all_results(start_zone INT, end_zone INT,did INT, seq INT, path_seq INT, \
        # node BIGINT,edge BIGINT,cost DOUBLE PRECISION,agg_cost DOUBLE PRECISION, \
        # link_cost DOUBLE PRECISION, id INT, geom GEOMETRY, lid BIGINT, start_node BIGINT, \
        # end_node BIGINT,ref_lids CHARACTER VARYING,ordering CHARACTER VARYING, \
        # speed NUMERIC, lanes BIGINT, fcn_class BIGINT, internal CHARACTER VARYING)")
        #
        # for x in range(int(len(id)/2)):
        #     nr_routes = routeSetGeneration(id[int(x)], id[int(x)+int(len(id)/2)]) # only even nr od-zones
        #     print("start: "+str(id[int(x)])+"   and end: "+str(id[int(x)+int(len(id)/2)]))

        # __________________________________________________________________________________________________________________
        #Start generating several route sets

        # List of OD-pairs
        #
        # start_list = [7954, 7954, 7954, 7954]
        #
        # end_list = [7990, 7949, 6913, 6950]
        #
        # print("cheers!")
        #
        # end_list = [7990, 7949, 6913, 6872]
        # start_list = [6904, 6884, 6869, 6887, 6954, 7317, 7304, 7541]
        # end_list = [6837, 7878, 7642, 7630, 7878, 6953, 7182, 7609]
        #
        # nr_routes = []
        # db.exec_("DROP TABLE if exists all_results")
        # db.exec_("CREATE TABLE all_results(start_zone INT, end_zone INT,did INT, seq INT, path_seq INT, \
        # node BIGINT,edge BIGINT,cost DOUBLE PRECISION,agg_cost DOUBLE PRECISION, \
        # link_cost DOUBLE PRECISION, id INT, geom GEOMETRY, lid BIGINT, start_node BIGINT, \
        # end_node BIGINT,ref_lids CHARACTER VARYING,ordering CHARACTER VARYING, \
        # speed NUMERIC, lanes BIGINT, fcn_class BIGINT, internal CHARACTER VARYING)")
        #
        # for x in range(len(end_list)):
        #     print("Generating start zone = "+str(start_list[x])+" end zone= "+str(end_list[x]))
        #
        #     nr_routes.append(routeSetGeneration(start_list[x], end_list[x], my, threshold))
        #___________________________________________________________________________________________________________________

        # Generating a single route set

        # start_zone = 6785
        # end_zone = 7405
        #
        # nr_routes = routeSetGeneration(start_zone, end_zone, my, threshold)
        # printRoutes(nr_routes)
        #
        #
        #
        #
        one_node = genStartNode(6785)
        onetoMany(one_node)
        toc();
        #___________________________________________________________________________________________________________________



if __name__ == "__main__" or __name__ == "__console__":
    main()




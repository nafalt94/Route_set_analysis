import time
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtSql import *
from PyQt5.QtWidgets import *
from qgis.core import QgsFeature, QgsGeometry, QgsProject

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
def comp(var1, var2, t):
    if var1 / var2 < t:
        return True
    else:
        return False
def removeRoutesLayers():
    layers = QgsProject.instance().mapLayers()

    for layer_id, layer in layers.items():
        if str(layer.name()) != "model_graph" and str(layer.name()) != "emme_zones" and str(layer.name()) != "labels" \
                and str(layer.name()) != "OpenStreetMap":
            QgsProject.instance().removeMapLayer(layer.id())
<<<<<<< HEAD
def genStartNode(start, end):
    query1 = db.exec_("SELECT start_node FROM(SELECT ROW_NUMBER() OVER (PARTITION BY id \
                    ORDER BY id, distance) AS score, id, lid, start_node, distance \
                    FROM( SELECT emme.id, lid,start_node, ST_distance(geom, emme_centroid) AS \
                    distance FROM model_graph, (SELECT id, ST_centroid(geom) AS \
                    emme_centroid, geom AS emme_geom FROM emme_zones WHERE id = " + str(start_zone) + " \
                    OR id = " + str(end_zone) + ") AS emme \
                    WHERE ST_Intersects(geom, emme_geom) ORDER BY distance) AS subq) AS subq \
                    WHERE score = 1")
=======


# End of Function definitions

TicToc = TicTocGenerator()
tic()


## Connect to the database
##################################
uri = QgsDataSourceUri()
# set host name, port, database name, username and password
uri.setConnection("localhost", "5432", "exjobb", "postgres", "password123")
# set database schema, table name, geometry column and optionally
# subset (WHERE clause)
vlayer = QgsVectorLayer(uri.uri(False), "layer name you like", "postgres")

print(uri.uri())

db = QSqlDatabase.addDatabase('QPSQL')



if db.isValid():
    print("QPSQL db is valid")
    # set the parameters needed for the connection
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

    start_zone = 7137
    end_zone = 7320

    # Starting points for the selected OD-pair
    query1 = db.exec_("SELECT * FROM(SELECT ROW_NUMBER() OVER (PARTITION BY id \
                ORDER BY id, distance) AS score, id, lid, start_node, distance \
                FROM( SELECT emme.id, lid,start_node, ST_distance(geom, emme_centroid) AS \
                distance FROM model_graph, (SELECT id, ST_centroid(geom) AS \
                emme_centroid, geom AS emme_geom FROM emme_zones WHERE id = " + str(start_zone) + " \
                OR id = " + str(end_zone) + ") AS emme \
                WHERE ST_Intersects(geom, emme_geom) ORDER BY distance) AS subq) AS subq \
                WHERE score = 1")


    zid = []
    lid = []
>>>>>>> c549359070df693a012d5ae0e0965640bd46d03b
    node = []
    counter = 0;
    # Saving SQL answer into matrix
    while query1.next():
        counter += 1
        node.append(query1.value(0))
    if counter != 2:
        raise Exception('No start or end node in Zones')
    return node
def routeSetGeneration(start, end):
    db.exec_("DROP TABLE if exists temp_table1")
    # Route 1
    db.exec_("SELECT * INTO temp_table1 from pgr_dijkstra('SELECT lid AS id, start_node AS source, end_node AS target, link_cost AS cost \
            ,3*link_cost AS reverse_cost FROM cost_table'," + start + "," + end + ") INNER JOIN cost_table ON(edge = lid)")

    # Saving route 1 in query
    temp_q = db.exec_("SELECT * FROM temp_table1 ORDER BY path_seq")
    queries = []
    queries.append(temp_q)

    # Result table creating
    db.exec_("DROP TABLE if exists result_table")
    db.exec_("SELECT " + str(start_zone) + " AS start_zone, " + str(end_zone) + " AS end_zone, 1 AS did,* INTO result_table FROM temp_table1")

    # Getting the agg. cost for best route
    cost_q = db.exec_("SELECT agg_cost FROM temp_table1 ORDER BY agg_cost DESC")

    cost_q.next()
    route1_cost = cost_q.value(0)
    print("Current cost route 1: " + str(route1_cost))
    route_stop = route1_cost

    ## Calculationg alternative routes
    i = 2

    nr_routes = 1

    while comp(route_stop, route1_cost, threshold):

        # Calculating penalizing term (P. 14 in thesis work)
        # Delta value
        delta_query = db.exec_("Select COUNT(*) from result_table")
        delta_query.next()
        delta = delta_query.value(0)

        # Parameter

        # Route 2
        db.exec_("DROP TABLE if exists temp_table2")
        route_2 = db.exec_("SELECT * INTO temp_table2 from pgr_dijkstra('SELECT id, source, target, CASE WHEN pen.cost IS NULL THEN subq.cost ELSE pen.cost END AS cost, reverse_cost \
                FROM (SELECT lid AS id, start_node AS source, end_node AS target, link_cost AS cost, 100000000 AS reverse_cost \
                FROM cost_table) AS subq \
                LEFT JOIN (select lid as edge, max(cost) + (max(cost)/(" + str(my) + " * min(cost)))*LN(" + str(delta) + ") AS cost from result_table group by lid ) AS pen ON \
                (subq.id = pen.edge)'," + start + "," + end + ")INNER JOIN cost_table ON(edge = lid)")

        # LEFT JOIN (SELECT edge, cost + (cost/"+str(my)+")*LN("+str(delta)+") AS cost FROM temp_table1) AS pen ON (subq.id = pen.edge)',"+start+","+end+")INNER JOIN model_graph.model_graph ON(edge = lid)")

        # Saving route i in query
        temp_q = db.exec_("SELECT * FROM temp_table2 ORDER BY path_seq")
        queries.append(temp_q)

        cost_q = db.exec_(
            "SELECT SUM(cost_table.link_cost) AS tot_cost FROM temp_table2 INNER JOIN cost_table ON cost_table.lid = temp_table2.lid;")
        cost_q.next()
        print("Current cost route " + str(i) + ": " + str(cost_q.value(0)))

        route_stop = cost_q.value(0)

        if comp(route_stop, route1_cost, threshold):
            db.exec_("INSERT INTO result_table SELECT " + str(start_zone) + " AS start_zone, " + str(end_zone) + " AS end_zone, " + str(
                i) + " AS did,*  FROM temp_table2")

            db.exec_("DROP TABLE if exists temp_table1")
            db.exec_("SELECT * INTO temp_table1 from temp_table2")
            i = i + 1
            nr_routes = nr_routes + 1
    return nr_routes
def printRoutes(nr_routes):
    i = 1
    while i <= nr_routes:
        sqlcall = "(SELECT * FROM result_table WHERE did=" + str(i) + ")"
        uri.setDataSource("", sqlcall, "geom", "", "lid")
        layert = QgsVectorLayer(uri.uri(), "route " + str(i), "postgres")
        QgsProject.instance().addMapLayer(layert)
        i = i + 1
<<<<<<< HEAD

# End of Function definitions

TicToc = TicTocGenerator()
tic()
removeRoutesLayers()

# Connect to the database can be done in functions if we make that work
uri = QgsDataSourceUri()
# set host name, port, database name, username and password
uri.setConnection("localhost", "5432", "exjobb", "postgres", "password123")
print(uri.uri())
db = QSqlDatabase.addDatabase('QPSQL')

# Variable definitions
my = 0.5
threshold = 1.5

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


    start_zone = 7137
    #start_zone = 7066
    end_zone = 7320
    #end_zone = 7748

    node = genStartNode(start_zone, end_zone)

    start = str(node[0])
    end = str(node[1])

    nr_routes = routeSetGeneration(start, end)

    printRoutes(nr_routes)


toc();




=======
>>>>>>> c549359070df693a012d5ae0e0965640bd46d03b

toc();


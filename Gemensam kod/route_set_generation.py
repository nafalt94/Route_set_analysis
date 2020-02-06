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
                and str(layer.name()) != "OpenStreetMap" and str(layer.name()) != "all_results" and str(layer.name()) != "Centroider":
            QgsProject.instance().removeMapLayer(layer.id())


def genStartNode(start, end):
    query1 = db.exec_("SELECT start_node FROM(SELECT ROW_NUMBER() OVER (PARTITION BY id \
                    ORDER BY id, distance) AS score, id, lid, start_node, distance \
                    FROM( SELECT emme.id, lid,start_node, ST_distance(geom, emme_centroid) AS \
                    distance FROM model_graph, (SELECT id, ST_centroid(geom) AS \
                    emme_centroid, geom AS emme_geom FROM emme_zones WHERE id = " + str(start) + " \
                    OR id = " + str(end) + ") AS emme \
                    WHERE ST_Intersects(geom, emme_geom) ORDER BY distance) AS subq) AS subq \
                    WHERE score = 1")
    node = []
    counter = 0;
    # Saving SQL answer into matrix
    while query1.next():
        counter += 1
        node.append(query1.value(0))
    if counter != 2:
        raise Exception('No start or end node in Zones and startnode is:' +str(start)+
                        ' and endnode is:'+ str(end))
    return node


def routeSetGeneration(start_zone, end_zone):
    node = genStartNode(start_zone, end_zone)
    start = node[0]
    end = node[1]
    print("Start zone is: "+str(start_zone)+" End zone is: "+str(end_zone))
    db.exec_("DROP TABLE if exists temp_table1")
    # Route 1
    db.exec_("SELECT * INTO temp_table1 from pgr_dijkstra('SELECT lid AS id, start_node AS source, end_node AS target, link_cost AS cost \
            ,3*link_cost AS reverse_cost FROM cost_table'," + str(start) + "," + str(end) + ") INNER JOIN cost_table ON(edge = lid)")

    # Saving route 1 in query
    temp_q = db.exec_("SELECT * FROM temp_table1 ORDER BY path_seq")
    queries = []
    queries.append(temp_q)

    # Result table creating
    db.exec_("DROP TABLE if exists result_table")
    db.exec_("SELECT " + str(start_zone) + " AS start_zone, " + str(end_zone) + " AS end_zone, 1 AS did,* INTO result_table FROM temp_table1")

    # Getting the agg. cost for best route
    cost_q = db.exec_("SELECT sum(link_cost) FROM temp_table1")

    cost_q.next()
    route1_cost = cost_q.value(0)
    print("Current cost route 1: " + str(route1_cost))
    route_stop = route1_cost

    pen_q = db.exec_("SELECT SUM(cost) from temp_table1")
    pen_q.next()
    print("Pencost för rutt: "+str(pen_q.value(0)))
    pen_stop = pen_q.value(0)

    ## Calculationg alternative routes
    i = 2

    nr_routes = 1

    while comp(route_stop, route1_cost, threshold):
        if pen_stop > 100000000:
            print("Warning: Pencost was over 1 billion")
            break
        # Calculating penalizing term (P. 14 in thesis work)
        # Delta value
        delta_query = db.exec_("Select COUNT(*) from result_table")
        delta_query.next()
        delta = delta_query.value(0)
        # Parameter

        # Route 2
        db.exec_("DROP TABLE if exists temp_table2")
        db.exec_("SELECT * INTO temp_table2 from pgr_dijkstra('SELECT id, source, target, \
        CASE WHEN pen.cost IS NULL THEN subq.cost ELSE pen.cost END AS cost, reverse_cost \
        FROM (SELECT lid AS id, start_node AS source, end_node AS target, link_cost AS cost, 100000000 AS reverse_cost \
        FROM cost_table) AS subq LEFT JOIN \
            (select lid as edge, max(cost) + (max(cost)/("+str(my)+" * min(cost)))*LN("+str(delta)+") AS cost \
        from result_table group by lid ) AS pen ON \
        (subq.id = pen.edge)',"+str(start)+","+str(end)+") INNER JOIN cost_table ON(edge = lid)")

        # Saving route cost without penalty.
        temp_q = db.exec_("SELECT * FROM temp_table2 ORDER BY path_seq")
        queries.append(temp_q)
        cost_q = db.exec_("SELECT SUM(cost_table.link_cost) AS tot_cost FROM temp_table2 INNER JOIN cost_table ON cost_table.lid = temp_table2.lid;")
        cost_q.next()
        print("Current cost route " + str(i) + ": " + str(cost_q.value(0)))
        route_stop = cost_q.value(0)
        print("difference is = " + str(route_stop / route1_cost))

        # Saving route cost with penalty.
        pen_q = db.exec_("SELECT SUM(cost) from temp_table2")
        pen_q.next()
        print("Pencost för rutt: "+str(pen_q.value(0)))
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


def printRoutes(nr_routes):
    i = 1
    while i <= nr_routes:
        sqlcall = "(SELECT * FROM result_table WHERE did=" + str(i) + ")"
        uri.setDataSource("", sqlcall, "geom", "", "lid")
        layert = QgsVectorLayer(uri.uri(), "route " + str(i), "postgres")
        QgsProject.instance().addMapLayer(layert)
        i = i + 1


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
threshold = 1.6

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
    #___________________________________________________________________________________________________________________
    # Generating "all" the route sets needed.
    # alla_od = db.exec_("SELECT id FROM emme_zones ORDER BY id")
    # id = []
    # while alla_od.next():
    #     id.append(alla_od.value(0))

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
    start_list = [6904, 6884, 6869, 6887, 6954, 7317, 7304]
    end_list = [7662, 7878, 7642, 7630, 7878, 6953,7182]
    # start_list = [7137, 7162]
    # end_list = [7320, 6836]

    nr_routes = []
    db.exec_("DROP TABLE if exists all_results")
    db.exec_("CREATE TABLE all_results(start_zone INT, end_zone INT,did INT, seq INT, path_seq INT, \
	node BIGINT,edge BIGINT,cost DOUBLE PRECISION,agg_cost DOUBLE PRECISION, \
	link_cost DOUBLE PRECISION, id INT, geom GEOMETRY, lid BIGINT, start_node BIGINT, \
    end_node BIGINT,ref_lids CHARACTER VARYING,ordering CHARACTER VARYING, \
    speed NUMERIC, lanes BIGINT, fcn_class BIGINT, internal CHARACTER VARYING)")

    for x in range(len(start_list)):
        nr_routes = routeSetGeneration(start_list[x], end_list[x] )

    #___________________________________________________________________________________________________________________

    # Generating a single route set

    # start_zone = 6785
    # end_zone = 7405
    # start_zone = 7154
    # end_zone = 7255
    #
    # nr_routes = routeSetGeneration(start_zone, end_zone)
    # printRoutes(nr_routes)


    #___________________________________________________________________________________________________________________


toc();

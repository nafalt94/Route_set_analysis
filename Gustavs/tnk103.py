## TIC TOC
import time

def TicTocGenerator():
    # Generator that returns time differences
    ti = 0           # initial time
    tf = time.time() # final time
    while True:
        ti = tf
        tf = time.time()
        yield tf-ti # returns the time difference

TicToc = TicTocGenerator() # create an instance of the TicTocGen generator

# This will be the main function through which we define both tic() and toc()
def toc(tempBool=True):
    # Prints the time difference yielded by generator instance TicToc
    tempTimeInterval = next(TicToc)
    if tempBool:
        print( "Elapsed time: %f seconds.\n" %tempTimeInterval )

def tic():
    # Records a time in TicToc, marks the beginning of a time interval
    toc(False)


from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtSql import *
from PyQt5.QtWidgets import *
from qgis.core import QgsFeature, QgsGeometry, QgsProject


tic()
## Connect to the database
##################################
uri = QgsDataSourceUri()
# set host name, port, database name, username and password
uri.setConnection("localhost", "5432", "postgres", "postgres", "gustav")
# set database schema, table name, geometry column and optionally
# subset (WHERE clause)
vlayer = QgsVectorLayer(uri.uri(False), "layer name you like", "postgres")

print(uri.uri())

db = QSqlDatabase.addDatabase('QPSQL')

if db.isValid():
        print ("QPSQL db is valid")   
        # set the parameters needed for the connection
        db.setHostName(uri.host())
        db.setDatabaseName(uri.database())
        db.setPort(int(uri.port()))
        db.setUserName(uri.username())
        db.setPassword(uri.password())
        # open (create) the connection
        if db.open():
            print ("Opened %s" % uri.uri())
        else:
            err = db.lastError()
            print (err.driverText())

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
        node = []

        # Saving SQL answer into matrix
        while query1.next():
            zid.append(query1.value(1))
            lid.append(query1.value(2))
            node.append(query1.value(3))

        print("Zone is: " + str(zid[0]))
        print("Node is: " + str(node[0]))
        print("Zone to link allocation finsihed")

        start = str(node[0])
        end = str(node[1])

        #start = str(42887)
        #end = str(42890)
        
      
        db.exec_("DROP TABLE if exists temp_table1")
        # Route 1 
        db.exec_("SELECT * INTO temp_table1 from pgr_dijkstra('SELECT lid AS id, start_node AS source, end_node AS target, link_cost AS cost \
        ,3*link_cost AS reverse_cost FROM cost_table',"+start+","+end+") INNER JOIN cost_table ON(edge = lid)")
        
        # Saving route 1 in query
        temp_q = db.exec_("SELECT * FROM temp_table1 ORDER BY path_seq")
        queries = []
        queries.append(temp_q)
        
        # Result table creating
        db.exec_("DROP TABLE if exists result_table")
        db.exec_("SELECT 1 AS did,* INTO result_table FROM temp_table1")
        #db.exec_("")
#        # Printing route 1 
#        sqlcall = "(SELECT * FROM temp_table1)"
#        uri.setDataSource("",sqlcall,"geom","","lid")
#        layer = QgsVectorLayer(uri.uri(),"route1","postgres")
#        QgsProject.instance().addMapLayer(layer)
        
        # Getting the agg. cost for best route
        cost_q = db.exec_("SELECT agg_cost FROM temp_table1 ORDER BY agg_cost DESC")
        
        cost_q.next()
        route1_cost = cost_q.value(0)
        print("Current cost "+str(route1_cost))
        route_stop = route1_cost
        
        ## Calculationg alternative routes
        i = 2
        
        threshold = 2.5
        nr_routes = 1
        print(route_stop/route1_cost)
        while route_stop/route1_cost < threshold: 
            print("Loopar")
            #print(route_stop)
            
            # Calculating penalizing term (P. 14 in thesis work)
            
            # Delta value
            delta_query = db.exec_("Select COUNT(*) from result_table")
            delta_query.next()
            delta = delta_query.value(0)
            
            # Parameter
            my = 0.5
            
            # Route 2
            db.exec_("DROP TABLE if exists temp_table2")
            route_2=db.exec_("SELECT * INTO temp_table2 from pgr_dijkstra('SELECT id, source, target, CASE WHEN pen.cost IS NULL THEN subq.cost ELSE pen.cost END AS cost, reverse_cost \
            FROM (SELECT lid AS id, start_node AS source, end_node AS target, link_cost AS cost, 100000000 AS reverse_cost \
            FROM cost_table) AS subq \
            LEFT JOIN (select lid as edge, max(cost) + (max(cost)/("+str(my)+" * min(cost)))*LN("+str(delta)+") AS cost from result_table group by lid ) AS pen ON \
            (subq.id = pen.edge)',"+start+","+end+")INNER JOIN cost_table ON(edge = lid)")
            
            #LEFT JOIN (SELECT edge, cost + (cost/"+str(my)+")*LN("+str(delta)+") AS cost FROM temp_table1) AS pen ON (subq.id = pen.edge)',"+start+","+end+")INNER JOIN model_graph.model_graph ON(edge = lid)")
            
            # Saving route i in query
            temp_q = db.exec_("SELECT * FROM temp_table2 ORDER BY path_seq")
            queries.append(temp_q)
            
            cost_q = db.exec_("SELECT SUM(cost_table.link_cost) AS tot_cost FROM temp_table2 INNER JOIN cost_table ON cost_table.lid = temp_table2.lid;")
            cost_q.next()
            print("Current cost:" + str(i) +":  " + str(cost_q.value(0)))

            route_stop = cost_q.value(0)
            print("test:")
            print(route_stop)
            
            if route_stop/route1_cost < threshold:
                db.exec_("INSERT INTO result_table SELECT "+str(i)+" AS did,*  FROM temp_table2")
            
                db.exec_("DROP TABLE if exists temp_table1")
                db.exec_("SELECT * INTO temp_table1 from temp_table2")
                i = i+1
                print(i)
                nr_routes = nr_routes + 1

        #Print costs for all selected routes
        #print(queries)
        
#        ## Printing from queries.
#        i=0
#        while i < 2:
#            print("Query"+str(i))
#            while queries[i].next():
#                print("seq:"+str(queries[i].value(1))+" lid:"+str(queries[i].value(3)))
#            
#            i=i+1
        i=1
        while i<= nr_routes:
            
            sqlcall = "(SELECT * FROM result_table WHERE did="+str(i)+")"
            uri.setDataSource("",sqlcall,"geom","","lid")
            layert = QgsVectorLayer(uri.uri(),"route "+str(i),"postgres")
            QgsProject.instance().addMapLayer(layert)
            i=i+1

        print("Testing pycharm")
toc();
####################################





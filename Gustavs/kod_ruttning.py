from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtSql import *
from PyQt5.QtWidgets import *
from qgis.core import QgsFeature, QgsGeometry, QgsProject


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
            
            
        start = str(42887)
        end = str(42890)

        db.exec_("DROP TABLE if exists temp_table1")
        db.exec_("SELECT * INTO temp_table1 from pgr_dijkstra('SELECT lid AS id, start_node AS source, end_node AS target, ST_length(geom)/speed*3.6 AS cost \
        ,10000000 AS reverse_cost FROM model_graph',"+start+","+end+") INNER JOIN model_graph ON(edge = lid)")

         # Result table creating
        db.exec_("DROP TABLE if exists result_table")
        db.exec_("SELECT 1 AS did,* INTO result_table FROM temp_table1")
        


        sqlcall = "(SELECT * FROM result_table WHERE did=1)"
        uri.setDataSource("",sqlcall,"geom","","lid")
        layert = QgsVectorLayer(uri.uri(),"route 1","postgres")
        QgsProject.instance().addMapLayer(layert)
        
        print("kod klar")



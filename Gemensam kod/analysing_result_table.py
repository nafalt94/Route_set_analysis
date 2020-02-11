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
# set host name, port, database name, username  db.exec_("SELECT ST_MakeLine(ST_Centroid(geom) ORDER BY id) AS geom into OD_lines FROM emme_zones"
#              " where id = "+str(start_list[0])+" OR id = "+ str(end_list[0]) +" ") and password
uri.setConnection("localhost", "5432", "exjobb", "postgres", "password123")
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

removed_lid = 83025 #Götgatan
#List of OD-pairs
start_list_selected = [6904, 6884, 6869, 6887, 6954, 7317, 7304, 7541]
end_list_selected = [7662, 7878, 7642, 7630, 7878, 6953, 7182,7609]

start_list_multiple = [6904, 6904, 6904, 6904, 6904, 6904, 6904, 6904]
end_list_multiple = [7662, 7878, 7642, 7630, 7878, 6953, 7182,7609]


create_tables(start_list_selected, end_list_selected,removed_lid)
#res = many_zones(start_list_multiple[0],end_list_multiple,removed_lid)
#print("Result is: "+ str(res))

toc();


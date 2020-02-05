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

# od_effect(start zone,end zone,LID of the removed link)
# Function returns proportion of extra cost of alternative route in relation to opt route
def odEffect(start, end, lid):
    start_zone = start
    end_zone = end
    removed_lid = lid

    #Finding best, non-affected alternative route
    query1 = db.exec_("SELECT MIN(did) FROM all_results WHERE"
                      " start_zone = "+str(start_zone)+" AND end_zone = "+str(end_zone)+" AND "
                                                                                        " did NOT IN (select did from all_results where lid = "+str(removed_lid)+")")
    query1.next()
    id_alt = str(query1.value(0))
    print("id_alt är: "+ id_alt)

    if id_alt== "NULL":
        #There is no routes with start and end zone
        return 1000;

    elif  id_alt == "1":
        #print("Zon påverkas inte")
        return 0
    else:
        #print("Zon påverkas och bästa id är:" + id_alt)

        # Fetching cost of the optimal route
        query2 = db.exec_("SELECT sum(link_cost) from all_results where "
                          " start_zone = "+str(start_zone)+" AND end_zone = "+str(end_zone)+" AND "
                                                                                            "did = 1 OR did = "+str(id_alt)+" group by did")
        query2.next()
        cost_opt = str(query2.value(0))
        #print("Cost of optimal route: " + cost_opt)

        # Alternative cost
        query2.next()
        cost_alt = str(query2.value(0))
        #print("Cost of alternative route: " + cost_alt)

        # Proportion of extra cost of alternative route in relation to opt route
        return (float(cost_alt)/float(cost_opt)-1)



start_zone = 7137
end_zone = 7320

#Trean bäst
#removed_lid = 80669
# Tvåan näst bäst
# removed_lid = 83896
# best påverkas ej
#removed_lid = 81118

removed_lid = 93383

#List of OD-pairs
start_list = [ 7137, 7162 ,7557, 6901, 6872]
end_list = [7320, 6836, 6968, 7934, 7985]

i=0
while i < len(start_list):
    result_test = odEffect(start_list[i], end_list[i], removed_lid)
    print("Result of "+str(i)+ " is: " + str(result_test))
    i = i+1


# result_test = odEffect(start_zone, end_zone,removed_lid)
# print("Result is: " + str(result_test))

toc();


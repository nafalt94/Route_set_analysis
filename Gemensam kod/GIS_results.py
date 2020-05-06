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

# Remove all GIS-layers except those stated in the function.
def removeRoutesLayers():
    layers = QgsProject.instance().mapLayers()

    for layer_id, layer in layers.items():
        if str(layer.name()) != "model_graph" and str(layer.name()) != "emme_zones" and str(layer.name()) != "labels" \
                and str(layer.name()) != "OpenStreetMap" and str(layer.name()) != "all_results" and str(
            layer.name()) != "Centroider" and str(layer.name()) != "dijk_result_table" and str(layer.name()) != "ata_lid"\
                and str(layer.name()) != "Link used by 3 shortest paths" and str(layer.name()) != "Link used by 0 shortest paths"\
                and str(layer.name()) != "OD_pairs" and str(layer.name()) != "failed_start_zones":
            QgsProject.instance().removeMapLayer(layer.id())

#Vet inte om dessa två behövs..
# Prints a route set based on whats in result_table.
def printRoutes(nr_routes):
    i = 1
    while i <= nr_routes:
        sqlcall = "(SELECT * FROM result_table WHERE did=" + str(i) + ")"
        uri.setDataSource("", sqlcall, "geom", "", "lid")
        layert = QgsVectorLayer(uri.uri(), " route " + str(i), "postgres")
        QgsProject.instance().addMapLayer(layert)
        i = i + 1

# Analysing all-to-all result for list and removed lid  # CANT decide where this should go either gis_layer or python.
def fetchResults(emme_result,max_failed):

    ############################ Create layer for mean deterioration
    sqlcall = "(SELECT * FROM "+str(emme_result)+" WHERE id NOT IN (SELECT origin FROM all_od_pairs_order " \
              " where status = 3 GROUP BY origin, assigned_to  HAVING count(*) > "+str(max_failed)+" ))"
    uri.setDataSource("", sqlcall, "geom", "", "id")

    layer = QgsVectorLayer(uri.uri(), "mean_deterioration ", "postgres")
    QgsProject.instance().addMapLayer(layer)

    values = (
        ('No deterioration', 0, 0, QColor.fromRgb(153, 204, 255)),
        ('Mean deterioration 1-5% ', 1, 1.05, QColor.fromRgb(102, 255, 102)),
        ('Mean deterioration 5-10% ', 1.05, 1.1, QColor.fromRgb(255, 255, 153)),
        ('Mean deterioration 10-20% ', 1.1, 1.2, QColor.fromRgb(255, 178, 102)),
        ('Mean deterioration 20-30% ', 1.2, 1.3, QColor.fromRgb(255, 102, 102)),
        ('All routes affected ', -1, -1, QColor.fromRgb(0, 0, 0)),
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
    sqlcall = "(select *, cast(nr_affected as float)/cast((SELECT count(distinct zone) FROM "+str(emme_result)+") as float) as prop_affected from "+str(emme_result)+"" \
              " WHERE id NOT IN (SELECT origin FROM all_od_pairs_order where status = 3 GROUP BY origin, assigned_to HAVING count(*) > "+str(max_failed)+") )"
    uri.setDataSource("", sqlcall, "geom", "", "id")

    layer = QgsVectorLayer(uri.uri(), "prop_affected ", "postgres")
    QgsProject.instance().addMapLayer(layer)

    values = (
        ('0 affected pairs', 0, 0, QColor.fromRgb(153, 204, 255)),
        ('1 affected pairs', 0.00000000000000000000001, 0.05, QColor.fromRgb(102, 255, 102)),
        ('1-5 affected pairs', 0.05, 0.2, QColor.fromRgb(255, 255, 153)),
        ('5-10 affected pairs', 0.2, 0.4, QColor.fromRgb(255, 178, 102)),
        ('10-many affected pairs', 0.4, 1, QColor.fromRgb(255, 102, 102)),
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
uri.setConnection("localhost", "5455", "mattugusna", "mattugusna", "password123")
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
    #removeRoutesLayers()

    if db.isValid():

        #Max allowed # of failing OD-pairs for zone to be included in analysis
        max_failed = 1160

        emme_result = "emme_results_grondalsbron"

        # Variable definitions
        fetchResults(emme_result,max_failed)
        toc();


if __name__ == "__main__" or __name__ == "__console__":
    main()

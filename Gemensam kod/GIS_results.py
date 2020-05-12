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
                and str(layer.name()) != "OD_pairs" and str(layer.name()) != "failed_start_zones" and str(layer.name()) != "clickable":
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
    sqlcall = "(SELECT * FROM "+str(emme_result)+" WHERE id NOT IN (SELECT origin FROM all_od_pairs_order_speed_limit " \
              " where status = 3 GROUP BY origin, assigned_to  HAVING count(*) > "+str(max_failed)+" ))"
    uri.setDataSource("", sqlcall, "geom", "", "id")

    layer = QgsVectorLayer(uri.uri(), "mean_deterioration ", "postgres")
    QgsProject.instance().addMapLayer(layer)

    ## create the renderer and assign it to a layer
    expression = 'mean_deterioration'  # field name
    myRenderer = QgsGraduatedSymbolRenderer(expression)
    myRenderer.setMode(QgsGraduatedSymbolRenderer.Jenks)
    myRenderer.updateClasses(layer, QgsGraduatedSymbolRenderer.Jenks, 5)
    # using color ramp visspec
    ramp = QgsCptCityColorRamp("cb/seq/Blues_09", "", False, True)
    # ramp = QgsGradientColorRamp.clone()
    myRenderer.updateColorRamp(ramp)
    layer.setRenderer(myRenderer)

    ############################ Create layer for nr_affected OD-pairs
    sqlcall = "(select *, cast(nr_affected as float)/cast((SELECT count(distinct zone) FROM "+str(emme_result)+") as float) as prop_affected from "+str(emme_result)+"" \
              " WHERE id NOT IN (SELECT origin FROM all_od_pairs_order_speed_limit where status = 3 GROUP BY origin, assigned_to HAVING count(*) > "+str(max_failed)+") )"
    uri.setDataSource("", sqlcall, "geom", "", "id")

    layer = QgsVectorLayer(uri.uri(), "prop_affected ", "postgres")
    QgsProject.instance().addMapLayer(layer)

    ## create the renderer and assign it to a layer
    expression = 'prop_affected'  # field name
    myRenderer = QgsGraduatedSymbolRenderer(expression)
    myRenderer.setMode(QgsGraduatedSymbolRenderer.Jenks)
    myRenderer.updateClasses(layer, QgsGraduatedSymbolRenderer.Jenks, 5)
    # using color ramp visspec
    ramp = QgsCptCityColorRamp("cb/seq/Blues_09", "", False, True)
    # ramp = QgsGradientColorRamp.clone()
    myRenderer.updateColorRamp(ramp)
    layer.setRenderer(myRenderer)

    ############################ Create layer for "factor score"
    sqlcall = "(select *, CASE WHEN mean_deterioration = -1 and nr_affected > 0 THEN " \
              " -1 ELSE cast(mean_deterioration-1 as float) * cast(nr_affected as float)/cast((SELECT count(distinct zone) " \
              " FROM " + str(emme_result) + ") as float)  END as factor_score from " + str(emme_result) + "" \
                    " WHERE id NOT IN (SELECT origin FROM all_od_pairs_order_speed_limit where status = 3 GROUP BY origin, assigned_to HAVING count(*) > " + str(
        max_failed) + ") )"
    uri.setDataSource("", sqlcall, "geom", "", "id")

    layer = QgsVectorLayer(uri.uri(), "factor_score ", "postgres")
    QgsProject.instance().addMapLayer(layer)

    ## create the renderer and assign it to a layer
    expression = 'factor_score'  # field name
    myRenderer = QgsGraduatedSymbolRenderer(expression)
    myRenderer.setMode(QgsGraduatedSymbolRenderer.Jenks)
    myRenderer.updateClasses(layer, QgsGraduatedSymbolRenderer.Jenks, 5)
    # using color ramp visspec
    ramp = QgsCptCityColorRamp("cb/seq/Greens_09", "", False, True)
    # ramp = QgsGradientColorRamp.clone()
    myRenderer.updateColorRamp(ramp)
    layer.setRenderer(myRenderer)


    ############################ Create layer for redirection zones
    sqlcall = "(select *, CASE WHEN mean_deterioration = -1 and nr_affected > 0 THEN " \
              " -1 ELSE  (1-cast(mean_deterioration-1 as float))^10* cast(nr_affected as float)/cast((SELECT count(distinct zone) " \
              " FROM " + str(emme_result) + ") as float)  END as factor_score_invers from " + str(emme_result) + "" \
                                                                                                          " WHERE id NOT IN (SELECT origin FROM all_od_pairs_order_speed_limit where status = 3 GROUP BY origin, assigned_to HAVING count(*) > " + str(
        max_failed) + ") )"
    uri.setDataSource("", sqlcall, "geom", "", "id")

    layer = QgsVectorLayer(uri.uri(), "factor_score_invers", "postgres")
    QgsProject.instance().addMapLayer(layer)

    ## create the renderer and assign it to a layer
    expression = 'factor_score_invers'  # field name
    myRenderer = QgsGraduatedSymbolRenderer(expression)
    myRenderer.setMode(QgsGraduatedSymbolRenderer.Jenks)
    myRenderer.updateClasses(layer, QgsGraduatedSymbolRenderer.Jenks, 5)
    # using color ramp visspec
    ramp = QgsCptCityColorRamp("cb/seq/Blues_09", "", False, True)
    # ramp = QgsGradientColorRamp.clone()
    myRenderer.updateColorRamp(ramp)
    layer.setRenderer(myRenderer)

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
    removeRoutesLayers()

    if db.isValid():

        #Max allowed # of failing OD-pairs for zone to be included in analysis
        max_failed = 1160

        emme_result = "emme_results_grondals_soder"
        emme_result = "emme_results_hela_sodermalm"

        # Variable definitions
        fetchResults(emme_result,max_failed)
        toc();


if __name__ == "__main__" or __name__ == "__console__":
    main()

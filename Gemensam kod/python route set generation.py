# Authors: Mattias Tunholm
# Date of creation: 2020-02-20

# Imports
import time
import psycopg2



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

def genonenode(zone):
    cur.execute("CREATE TABLE IF NOT EXISTS od_lid AS (SELECT * FROM(SELECT ROW_NUMBER() OVER (PARTITION BY id \
                ORDER BY id, distance) AS score, id, lid, start_node, distance \
                FROM(SELECT emme.id, lid, start_node, ST_distance(geom, emme_centroid) AS \
                distance FROM model_graph, (SELECT id, ST_centroid(geom) AS \
                emme_centroid, geom AS emme_geom FROM emme_zones WHERE id > 0) AS emme \
                WHERE ST_Intersects(geom, emme_geom) ORDER BY distance) AS subq) AS subq \
                WHERE score = 1)")



    cur.execute("SELECT start_node FROM od_lid WHERE id=" + str(zone))
    result = cur.fetchone()
    print("THE NODE" + str(result[0]))
    if result is not None:
        node = result[0]
    else:
        raise Exception('No node in zones:' + str(zone))

    # # Saving SQL answer into matrix
    # while query1.next():
    #     counter1 += 1
    #     # print("node is :" + str(query1.value(0)))
    #     node = query1.value(0)
    #
    # if counter1 != 1:
    #     raise Exception('No  node in Zones and startnode is:' + str(zone))

    return node


def routeSetGeneration(start_zone, end_zone, my, threshold):

    db.exec_("CREATE TABLE IF NOT EXISTS cost_table AS (select ST_Length(geom)/speed*3.6 AS link_cost, * \
    from model_graph)")

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
    #print("Current cost route 1: " + str(route1_cost))
    #route_stop = route1_cost

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
        if nr_routes >= 10:
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
            (select lid as edge, max(cost) + (max(cost)/(" + str(my) + " * min(cost)))*LN(" + str(delta) + ") AS cost \
        from result_table group by lid ) AS pen ON \
        (subq.id = pen.edge)'," + str(start) + "," + str(end) + ") INNER JOIN cost_table ON(edge = lid)")

        # Saving route cost without penalty and updating route_stop.
        cost_q = db.exec_("SELECT SUM(cost_table.link_cost) AS tot_cost FROM temp_table2 \
        INNER JOIN cost_table ON cost_table.lid = temp_table2.lid;")
        cost_q.next()
        route_stop = cost_q.value(0)
        # print("Current cost route " + str(i) + ": " + str(cost_q.value(0)))

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
            testa = db.exec_("SELECT cast(count(*) as float) / (SELECT COUNT(*) FROM result_table WHERE did="+str(i)+") AS per \
            FROM (SELECT did,lid FROM result_table WHERE did="+str(i)+" and lid = ANY(SELECT lid FROM result_table \
            WHERE NOT did >= "+str(i)+") group by lid,did) as foo")
            testa.next()
            print("rutt " + str(i) + " " + str(testa.value(0)) + " länkar överlappar!")

            db.exec_("DROP TABLE if exists temp_table1")
            db.exec_("SELECT * INTO temp_table1 from temp_table2")
            i = i + 1
            nr_routes = nr_routes + 1
        else:
            break

    db.exec_("INSERT INTO all_results SELECT * FROM result_table")
    print("all results inserted")
    return nr_routes

# Connection global to be used everywhere.
conn = psycopg2.connect(host="localhost", database="exjobb", user="postgres", password="password123")
cur = conn.cursor()

def main():

    cur.execute("SELECT * FROM od_lid limit 10")
    print("FETCHED"+str(cur.fetchall()))

    print("GENNODE::"+str(genonenode(7950)))

    # Variable definitions
    my = 0.3
    threshold = 1.6

# ___________________________________________________________________________________________________________________

# __________________________________________________________________________________________________________________


    #Close connection and cursor

if __name__ == "__main__" or __name__ == "__console__":
    main()

cur.close()
conn.close()
toc();
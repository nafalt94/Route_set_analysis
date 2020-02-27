# Authors: Mattias Tunholm
# Date of creation: 2020-02-20

# Imports
import time
import psycopg2
import numpy as np



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

# Send in zone number and get start node number of that zone.
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


    cur.execute("CREATE TABLE IF NOT EXISTS cost_table AS (select ST_Length(geom)/speed*3.6 AS link_cost, * \
    from model_graph)")
    cur.execute("CREATE TABLE IF NOT EXISTS all_results(start_zone INT, end_zone INT,did INT, seq INT, path_seq INT, \
            node BIGINT,edge BIGINT,cost DOUBLE PRECISION,agg_cost DOUBLE PRECISION, \
            link_cost DOUBLE PRECISION, id INT, geom GEOMETRY, lid BIGINT, start_node BIGINT, \
            end_node BIGINT,ref_lids CHARACTER VARYING,ordering CHARACTER VARYING, \
            speed NUMERIC, lanes BIGINT, fcn_class BIGINT, internal CHARACTER VARYING)")

    start = genonenode(start_zone)
    end = genonenode(end_zone)

    #print("Start node is: "+str(start)+" End node is: "+str(end))

    cur.execute("DROP TABLE if exists temp_table1")
    # Route 1
    cur.execute("SELECT * INTO temp_table1 from pgr_dijkstra('SELECT lid AS id, start_node AS source, end_node AS target, \
     link_cost AS cost, 1000 AS reverse_cost FROM cost_table'," + str(start) + "," + str(end) + ") \
     INNER JOIN cost_table ON(edge = lid)")


    # Result table creating
    cur.execute("DROP TABLE if exists result_table")
    cur.execute("SELECT " + str(start_zone) + " AS start_zone, " + str(end_zone) + " AS end_zone, 1 AS did,* INTO \
    result_table FROM temp_table1")

    # Getting total cost for route 1 and setting first stop criterion.
    cur.execute("SELECT sum(link_cost) FROM temp_table1")
    route1_cost = cur.fetchone()[0]
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
        if nr_routes >= 100000:
            print("Warning: The number of routes was over 10 for start zone: \
            " + str(start_zone) + " and end zone: " + str(end_zone))
            break

        # Calculating penalizing term (P. 14 in thesis work)
        # Delta value
        cur.execute("Select COUNT(*) from result_table")
        delta = cur.fetchone()[0]

        #print("DELTA VALUE IS =:"+str(delta))
        # Parameter

        # Route 2
        cur.execute("DROP TABLE if exists temp_table2")
        cur.execute("SELECT * INTO temp_table2 FROM pgr_dijkstra('SELECT id, source, target, \
        CASE WHEN pen.cost IS NULL THEN subq.cost ELSE pen.cost END AS cost, reverse_cost \
        FROM (SELECT lid AS id, start_node AS source, end_node AS target, link_cost AS cost, 1000 AS reverse_cost \
        FROM cost_table) AS subq LEFT JOIN \
            (select lid as edge, max(cost) + (max(cost)/(" + str(my) + " * min(cost)))*LN(" + str(delta) + ") AS cost \
        from result_table group by lid ) AS pen ON \
        (subq.id = pen.edge)'," + str(start) + "," + str(end) + ") INNER JOIN cost_table ON(edge = lid)")

        # Saving route cost without penalty and updating route_stop.
        cur.execute("SELECT SUM(cost_table.link_cost) AS tot_cost FROM temp_table2 \
        INNER JOIN cost_table ON cost_table.lid = temp_table2.lid;")
        route_stop = cur.fetchone()[0]
        #route_stop = cost_q.value(0)
        #print("Current cost route " + str(i) + ": " + str(route_stop))

        # print("difference is = " + str(route_stop / route1_cost))

        # Saving route cost with penalty. Remove comment if  penalty want to be used as breaking criterion
        # pen_q = db.exec_("SELECT SUM(cost) from temp_table2")
        # pen_q.next()
        # # print("Pencost för rutt: "+str(pen_q.value(0)))
        # pen_stop = pen_q.value(0)

        if comp(route_stop, route1_cost, threshold):
            cur.execute("INSERT INTO result_table SELECT " + str(start_zone) + " AS start_zone, " + str(
                end_zone) + " AS end_zone, " + str(
                i) + " AS did,*  FROM temp_table2")
            # Coverage calculation here.
            cur.execute("SELECT sum(st_length(geom)) / (SELECT sum(st_length(geom)) FROM result_table WHERE \
            did="+str(i)+") AS per FROM (SELECT did,lid,geom FROM result_table WHERE did="+str(i)+" and lid = \
            ANY(SELECT lid FROM result_table WHERE NOT did >= "+str(i)+") group by lid,did,geom) as foo")
            coverage = cur.fetchone()
            #print("rutt " + str(i) + " " + str(coverage) + " länkar överlappar!")

            cur.execute("DROP TABLE if exists temp_table1")
            cur.execute("SELECT * INTO temp_table1 from temp_table2")
            i = i + 1
            nr_routes = nr_routes + 1
        else:
            break

    cur.execute("INSERT INTO all_results SELECT * FROM result_table")
    conn.commit()
    #print("all results inserted")



    return nr_routes


# Generates result table for selected OD-pairs
def selectedODResultTable(start_list, end_list, my, threshold, removed_lids):

    nr_routes = []
    cur.execute("DROP TABLE if exists all_results")
    cur.execute("CREATE TABLE all_results(start_zone INT, end_zone INT,did INT, seq INT, path_seq INT, \
    node BIGINT,edge BIGINT,cost DOUBLE PRECISION,agg_cost DOUBLE PRECISION, \
    link_cost DOUBLE PRECISION, id INT, geom GEOMETRY, lid BIGINT, start_node BIGINT, \
    end_node BIGINT,ref_lids CHARACTER VARYING,ordering CHARACTER VARYING, \
    speed NUMERIC, lanes BIGINT, fcn_class BIGINT, internal CHARACTER VARYING)")

    # Table with removed lids so we can run python code without syncing to much with gis_layer_creation.
    cur.execute("DROP TABLE if exists removed_lids")
    cur.execute("CREATE TABLE removed_lids(lid BIGINT)")

    for x in removed_lids:
        cur.execute("INSERT INTO removed_lids SELECT "+str(x)+" AS lid")

    for x in range(len(end_list)):
        print("Generating start zone = " + str(start_list[x]) + " end zone= " + str(end_list[x]))

        nr_routes.append(routeSetGeneration(start_list[x], end_list[x], my, threshold))
        print("Nr of routes"+str(nr_routes))

def allToAllResultTable(all_list, my, threshold, removed_lids):
    # Table with removed lids so we can run python code without syncing to much with gis_layer_creation.
    cur.execute("DROP TABLE if exists removed_lids")
    cur.execute("CREATE TABLE removed_lids(lid BIGINT)")

    for x in removed_lids:
        cur.execute("INSERT INTO removed_lids SELECT " + str(x) + " AS lid")


    nr_routes = []
    cur.execute("DROP TABLE if exists all_results")
    cur.execute("CREATE TABLE all_results(start_zone INT, end_zone INT,did INT, seq INT, path_seq INT, \
    node BIGINT,edge BIGINT,cost DOUBLE PRECISION,agg_cost DOUBLE PRECISION, \
    link_cost DOUBLE PRECISION, id INT, geom GEOMETRY, lid BIGINT, start_node BIGINT, \
    end_node BIGINT,ref_lids CHARACTER VARYING,ordering CHARACTER VARYING, \
    speed NUMERIC, lanes BIGINT, fcn_class BIGINT, internal CHARACTER VARYING)")

    for y in range(len(all_list)):
        for x in range(len(all_list)):
            # From and to same zone is not interesting
            if y != x:
                nr_routes.append(routeSetGeneration(all_list[y], all_list[x], my, threshold))
        progress = y/len(all_list)
        print("Patience! This is difficult, you know...  Progress:" + str(progress) + "%")

def getAllNodes():
    cur.execute("CREATE TABLE IF NOT EXISTS od_lid AS (SELECT * FROM(SELECT ROW_NUMBER() OVER (PARTITION BY id \
                   ORDER BY id, distance) AS score, id, lid, start_node, distance \
                   FROM(SELECT emme.id, lid, start_node, ST_distance(geom, emme_centroid) AS \
                   distance FROM model_graph, (SELECT id, ST_centroid(geom) AS \
                   emme_centroid, geom AS emme_geom FROM emme_zones WHERE id > 0) AS emme \
                   WHERE ST_Intersects(geom, emme_geom) ORDER BY distance) AS subq) AS subq \
                   WHERE score = 1)")

    cur.execute("SELECT start_node, id FROM od_lid")
    result = cur.fetchall()
    node_list = []
    # Saving SQL answer into matrix
    for row in result:
        node_list.append(row[0])
    return node_list

# Generate shortest path between one_node to all the other
def onetoMany(one_zone):
    print("one to many")
    one_node = genonenode(one_zone)
    cur.execute("DROP TABLE if exists dijk_test")
    cur.execute("SELECT * INTO dijk_test FROM pgr_Dijkstra('SELECT lid AS id, start_node AS source, \
    end_node AS target, ST_length(geom)/speed*3.6 AS cost, 100000 AS reverse_cost \
    FROM model_graph'," + str(one_node) + ", ARRAY(SELECT start_node FROM od_lid WHERE NOT \
    (start_node='" + str(one_node) + "'))) INNER JOIN cost_table ON(edge = lid) ")
    conn.commit()

# Generate one to many with penalty OBS not working correctly
def onetoManyPenalty(one_node, many_nodes_list, my):
    print("one to many with penalty")

    print(str(one_node) + "  " + str(many_nodes_list))

    # Route 1
    cur.execute("DROP TABLE if exists dijk_temp_table1")
    cur.execute("SELECT " + str(one_node) + " AS one_node,* INTO dijk_temp_table1 FROM pgr_Dijkstra('SELECT lid AS id, start_node AS source, \
        end_node AS target, ST_length(geom)/speed*3.6 AS cost, 100000 AS reverse_cost \
        FROM model_graph'," + str(one_node) + ", ARRAY(SELECT start_node FROM od_lid \
        WHERE start_node='" + str(many_nodes_list[0]) + "' or start_node='" + str(many_nodes_list[1]) + "' or \
        start_node='" + str(many_nodes_list[2]) + "') ) \
        INNER JOIN cost_table ON(edge = lid) ")

    cur.execute("DROP TABLE if exists dijk_result_table")
    cur.execute("SELECT 0 as delta, 1 AS did,* INTO \
        dijk_result_table FROM dijk_temp_table1")
    print("Route 1 inserted into dijk_result table!!")
    # Route 1 FINISHED

    # Route 2-X
    i = 2

    nr_routes = 1
    while i < 5:

        # Calculate delta an insert into the right penalty.
        for x in many_nodes_list:
            cur.execute("Select COUNT(*) from dijk_result_table WHERE one_node ='" + str(one_node)
                                   + "' and end_vid='" + str(x) + "'")
            delta = cur.fetchone()[0]
            print("delta value for " + str(x) + " is " + str(delta))
            cur.execute("UPDATE dijk_result_table SET delta =" + str(delta) + " WHERE one_node='" + str(one_node)
                     + "' and end_vid='" + str(x) + "' and did = "+str(i-1)+"")

        cur.execute("DROP TABLE if exists dijk_temp_table2")
        cur.execute("SELECT " + str(one_node) + " AS one_node,* INTO dijk_temp_table2 \
        FROM pgr_dijkstra('SELECT id, source, target, CASE WHEN pen.cost IS NULL THEN subq.cost \
        ELSE pen.cost END AS cost, reverse_cost FROM (SELECT lid AS id, start_node AS source, \
        end_node AS target, link_cost AS cost, 100000 AS reverse_cost FROM cost_table) AS subq LEFT JOIN \
        (select lid as edge, max(cost) + (max(cost)/(" + str(my) + " * min(cost)))*LN(delta) AS cost \
        from dijk_result_table group by lid, end_vid, delta) AS pen ON \
        (subq.id = pen.edge)'," + str(one_node) + ", ARRAY(SELECT start_node FROM od_lid \
        WHERE start_node='" + str(many_nodes_list[0]) + "' or start_node='" + str(many_nodes_list[1]) + "' or \
        start_node='" + str(many_nodes_list[2]) + "') ) INNER JOIN cost_table ON(edge = lid)")

        cur.execute("INSERT INTO dijk_result_table SELECT 0 AS delta, " + str(i) + " AS did,*  FROM dijk_temp_table2")
        print("Route " + str(i) + " inserted into dijk_result table!!")
        cur.execute("DROP TABLE if exists dijk_temp_table1")
        cur.execute("SELECT * INTO dijk_temp_table1 from dijk_temp_table2")
        i = i + 1
        nr_routes = nr_routes + 1

    conn.commit()

def route_set_lenght(nr_routes):

    print("Route set length called.")
    cur.execute("SELECT SUM(ST_LENGTH(geom)) as total_length FROM all_results")
    temp_l = cur.fetchone()[0]

    avg_len = temp_l / nr_routes
    return avg_len

def route_set_generation_tube(start_zone, end_zone, my, threshold, range):
    print("TUBE IT UP! :"+str(range))

    cur.execute("CREATE TABLE IF NOT EXISTS cost_table AS (select ST_Length(geom)/speed*3.6 AS link_cost, * \
    from model_graph)")
    cur.execute("CREATE TABLE IF NOT EXISTS all_results(start_zone INT, end_zone INT,did INT, seq INT, path_seq INT, \
            node BIGINT,edge BIGINT,cost DOUBLE PRECISION,agg_cost DOUBLE PRECISION, \
            link_cost DOUBLE PRECISION, id INT, geom GEOMETRY, lid BIGINT, start_node BIGINT, \
            end_node BIGINT,ref_lids CHARACTER VARYING,ordering CHARACTER VARYING, \
            speed NUMERIC, lanes BIGINT, fcn_class BIGINT, internal CHARACTER VARYING)")

    start = genonenode(start_zone)
    end = genonenode(end_zone)

    #print("Start node is: "+str(start)+" End node is: "+str(end))

    cur.execute("DROP TABLE if exists temp_table1")
    # Route 1
    cur.execute("SELECT * INTO temp_table1 from pgr_dijkstra('SELECT lid AS id, start_node AS source, end_node AS target, \
     link_cost AS cost, 1000 AS reverse_cost FROM cost_table'," + str(start) + "," + str(end) + ") \
     INNER JOIN cost_table ON(edge = lid)")


    # Result table creating
    cur.execute("DROP TABLE if exists result_table")
    cur.execute("SELECT " + str(start_zone) + " AS start_zone, " + str(end_zone) + " AS end_zone, 1 AS did,* INTO \
    result_table FROM temp_table1")

    # Getting total cost for route 1 and setting first stop criterion.
    cur.execute("SELECT sum(link_cost) FROM temp_table1")
    route1_cost = cur.fetchone()[0]
    print("Current cost route 1: " + str(route1_cost))
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
        if nr_routes >= 100000:
            print("Warning: The number of routes was over 10 for start zone: \
            " + str(start_zone) + " and end zone: " + str(end_zone))
            break

        # Calculating penalizing term (P. 14 in thesis work)
        # Delta value
        cur.execute("Select COUNT(*) from result_table")
        delta = cur.fetchone()[0]

        #print("DELTA VALUE IS =:"+str(delta))
        # Parameter

        # Route 2
        cur.execute("DROP TABLE if exists temp_table2")
        cur.execute("SELECT * INTO temp_table2 FROM pgr_dijkstra('SELECT id, source, target, \
        CASE WHEN pen.cost IS NULL THEN subq.cost ELSE pen.cost END AS cost, reverse_cost \
        FROM (SELECT lid AS id, start_node AS source, end_node AS target, link_cost AS cost, 1000 AS reverse_cost \
        FROM cost_table) AS subq LEFT JOIN \
            (select a.lid as edge, max(cost) + (max(cost)/(" + str(my) + " * min(cost)))*LN(" + str(delta) + ") AS cost \
        FROM model_graph AS a INNER JOIN result_table AS b ON (ST_DWithin(a.geom,b.geom," + str(range) + ")) group by a.lid ) AS pen ON \
        (subq.id = pen.edge)'," + str(start) + "," + str(end) + ") INNER JOIN cost_table ON(edge = lid)")

        # Saving route cost without penalty and updating route_stop.
        cur.execute("SELECT SUM(cost_table.link_cost) AS tot_cost FROM temp_table2 \
        INNER JOIN cost_table ON cost_table.lid = temp_table2.lid;")
        route_stop = cur.fetchone()[0]

        print("Current cost route " + str(i) + ": " + str(route_stop))

        # print("difference is = " + str(route_stop / route1_cost))

        # Saving route cost with penalty. Remove comment if  penalty want to be used as breaking criterion
        # pen_q = db.exec_("SELECT SUM(cost) from temp_table2")
        # pen_q.next()
        # print("Pencost för rutt: "+str(pen_q.value(0)))
        # pen_stop = pen_q.value(0)

        if comp(route_stop, route1_cost, threshold):
            cur.execute("INSERT INTO result_table SELECT " + str(start_zone) + " AS start_zone, " + str(
                end_zone) + " AS end_zone, " + str(
                i) + " AS did,*  FROM temp_table2")
            # Coverage calculation here.
            cur.execute("SELECT sum(st_length(geom)) / (SELECT sum(st_length(geom)) FROM result_table WHERE \
            did="+str(i)+") AS per FROM (SELECT did,lid,geom FROM result_table WHERE did="+str(i)+" and lid = \
            ANY(SELECT lid FROM result_table WHERE NOT did >= "+str(i)+") group by lid,did,geom) as foo")
            coverage = cur.fetchone()
            print("rutt " + str(i) + " " + str(coverage) + " länkar överlappar!")

            cur.execute("DROP TABLE if exists temp_table1")
            cur.execute("SELECT * INTO temp_table1 from temp_table2")
            i = i + 1
            nr_routes = nr_routes + 1
        else:
            break

    cur.execute("INSERT INTO all_results SELECT * FROM result_table")
    conn.commit()
    #print("all results inserted")



    return nr_routes



# End of function definitions

# Connection global to be used everywhere.
conn = psycopg2.connect(host="localhost", database="exjobb", user="postgres", password="password123")
cur = conn.cursor()

def main():
    tic()

    # Variable definitions
    my = 1
    threshold = 1.6

    # Which zones to route between
    start = 7317
    end = 6953

    # Which zones in list to route between
    start_list = [6904, 6884, 6869, 6887, 6954, 7317, 7304, 7541]
    end_list = [6837, 6776, 7642, 7630, 7878, 6953, 7182, 7609]

    all_list = [8005, 7195, 6884, 6837, 6776, 7835, 7864, 6955, 7570, 7422, 7680, 7557, 7560, 6879, 6816, 7630, 7162,
                7187, 7227]
    smaller_list = [8005, 7195, 6884, 6837, 6776]

    # Which lids to remove
    removed_lid = [89227]  # Götgatan, [83025] för Söderledstunneln
    #removed_lids = [83025, 84145] # [81488, 83171] för Essingeleden, [83025, 84145] för Söderleden

    # Uncomment what typ of method you want to use.

    # Single route set

    # 0.11, 0.12, 0.13, 0.14, 0.15, 0.16, 0.17, 0.18, 0.19,
    # my_list = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1]
    # 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1
    # j = 0
    # while j < len(my_list):
    #     cur.execute("DROP TABLE if exists all_results")
    #     nr_routes = routeSetGeneration(start, end, my_list[j], threshold)
    #     len_rs = route_set_lenght(nr_routes)
    #     print("my is :" + str(my_list[j]) + " and average length is :" + str(len_rs) + " nr of routes is:"+str(nr_routes))
    #     j += 1
    # cur.execute("DROP TABLE if exists all_results")
    # range = 1
    # route_set_generation_tube(start,end,my,threshold,range)
    #routeSetGeneration(start,end,my,threshold)
    onetoMany(6904)

    # Generate OD-pairs route sets between the zones in start_list and end_list
    # selectedODResultTable(start_list, end_list, my, threshold, removed_lid)

    # Generate all in list to all in list
    #allToAllResultTable(smaller_list, my, threshold, removed_lid)



if __name__ == "__main__" or __name__ == "__console__":
    main()

#Close connection and cursor
conn.commit()
cur.close()
conn.close()
toc();
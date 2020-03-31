# Authors: Mattias Tunholm
# Date of creation: 2020-02-20

# Imports
import time
import sys
from datetime import datetime
import psycopg2
import numpy as np

#For att fa MAC-address
from uuid import getnode as get_mac




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
        # print("Elapsed time: %f seconds.\n" % tempTimeInterval)
        return tempTimeInterval


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
                WHERE ST_Intersects(geom, emme_geom) ORDER BY distance, lid desc) AS subq) AS subq \
                WHERE score = 1)")


    cur.execute("SELECT start_node FROM od_lid WHERE id=" + str(zone))
    result = cur.fetchone()


    if result is not None:
        node = result[0]
    else:
        raise Exception('No node in zones:' + str(zone))
        # print("No node in zones:"+ str(zone))
        # node = -1
    # # Saving SQL answer into matrix
    # while query1.next():
    #     counter1 += 1
    #     # print("node is :" + str(query1.value(0)))
    #     node = query1.value(0)
    #
    # if counter1 != 1:
    #     raise Exception('No  node in Zones and startnode is:' + str(zone))

    return node

# Route set generation who only adds to all results.

def routeSetGeneration(start_zone, end_zone, my, threshold,max_overlap):

    cur.execute("CREATE TABLE IF NOT EXISTS cost_table AS (select ST_Length(geom)/speed*3.6 AS link_cost, * \
    from model_graph)")
    cur.execute("CREATE TABLE IF NOT EXISTS all_results(did INT, start_zone INT, end_zone INT, lid BIGINT, node BIGINT, \
               geom geometry,cost double precision,link_cost DOUBLE PRECISION, start_node BIGINT, end_node BIGINT,path_seq INT,agg_cost DOUBLE PRECISION, \
               speed numeric, fcn_class BIGINT, my DOUBLE PRECISION, time DOUBLE PRECISION)")

    start = genonenode(start_zone)
    end = genonenode(end_zone)
    print("Start zone is:"+str(start_zone))
    print("End zone is:"+str(end_zone))
    print("Start node is: "+str(start)+" End node is: "+str(end))

    cur.execute("DROP TABLE if exists temp_table1")
    # Route 1
    cur.execute("SELECT * INTO temp_table1 from pgr_dijkstra('SELECT lid AS id, start_node AS source, end_node AS target, \
     link_cost AS cost, 1000000 AS reverse_cost FROM cost_table'," + str(start) + "," + str(end) + ") \
     INNER JOIN cost_table ON(edge = lid)")



    # Getting total cost for route 1 and setting first stop criterion.
    cur.execute("SELECT sum(link_cost) FROM temp_table1")

    route1_cost = cur.fetchone()[0]
    print("Current cost route 1: " + str(route1_cost))
    route_stop = route1_cost



    cur.execute("SELECT max(agg_cost) FROM temp_table1")
    reverse = cur.fetchone()[0]

    if route_stop is None or reverse > 1000000:
    # Result table creating
        if route_stop is None:
            # print("No route BEFORE WHILE LOOP")
            cur.execute("DROP TABLE if exists result_table")
        else:
            # print("reverse activated to high!")
            cur.execute("DROP TABLE if exists result_table")
    else:
        cur.execute("DROP TABLE if exists result_table")
        cur.execute("SELECT 1 AS did, " + str(start_zone) + " AS start_zone, " + str(end_zone) + " AS end_zone, lid, node, \
        geom, cost, link_cost,start_node, end_node, path_seq, agg_cost, speed, fcn_class, "+str(my)+" as my, 0.0 as time INTO \
        result_table FROM temp_table1")

        # # Pen cost as breaking if stuck instead of nr_routes
        # pen_q = db.exec_("SELECT SUM(cost) from temp_table1")
        # pen_q.next()
        # # print("Pencost för rutt: "+str(pen_q.value(0)))
        # pen_stop = pen_q.value(0)

        # Calculationg alternative routes
        i = 2
        nr_routes = 1

        # Count if overlap and nr_route is the same too many times (short OD-pairs with no routes)
        overlap_count = 0

        # while comp(route_stop, route1_cost, threshold):
        while True:
            #print("Route stop is ="+str(route_stop)+" and distance is ="+str(distance))
            if nr_routes >= 100 or route_stop is None or route_stop > 1000000:
                if nr_routes >= 100:
                    print("Warning: The number of routes was over 100 for start zone: \
                    " + str(start_zone) + " and end zone: " + str(end_zone))
                if route_stop is None:
                    print("No route between zone "+str(start_zone)+" and zone "+str(end_zone))
                if route_stop is not None:
                    if route_stop >= 1000000:
                        print("Warning reverse cost used in the while loop")
                break

            # Calculating penalizing term (P. 14 in thesis work)
            # Delta value
            cur.execute("Select COUNT(*) from result_table")
            delta = cur.fetchone()[0]

            #print("DELTA VALUE IS =:"+str(delta))
            # Parameter

            # Route 2
            cur.execute("DROP TABLE if exists temp_table2")

            # Normal penalty
            cur.execute("SELECT * INTO temp_table2 FROM pgr_dijkstra('SELECT id, source, target, \
            CASE WHEN pen.cost IS NULL THEN subq.cost ELSE pen.cost END AS cost, reverse_cost \
            FROM (SELECT lid AS id, start_node AS source, end_node AS target, link_cost AS cost, 1000000 AS reverse_cost \
            FROM cost_table) AS subq LEFT JOIN \
                (select lid as edge, max(cost) + (max(cost)/(" + str(my) + " * " + str(route_stop) + "))*LN(" + str(delta) + ") AS cost \
            from result_table group by lid ) AS pen ON \
            (subq.id = pen.edge)'," + str(start) + "," + str(end) + ") INNER JOIN cost_table ON(edge = lid)")

            # Saving route cost without penalty and updating route_stop.
            cur.execute("SELECT SUM(cost_table.link_cost) AS tot_cost FROM temp_table2 \
            INNER JOIN cost_table ON cost_table.lid = temp_table2.lid;")
            route_stop = cur.fetchone()[0]

            print("Current cost route " + str(i) + ": " + str(route_stop))


            if comp(route_stop, route1_cost, threshold):

                # Check if overlap for route is too high
                cur.execute("SELECT coalesce(sum(st_length(geom)) / (SELECT sum(st_length(geom)) FROM temp_table2 ),0) AS per "
                            "FROM (SELECT lid,geom FROM temp_table2 WHERE lid = "
                            "ANY(SELECT lid FROM result_table) group by lid,geom) as foo")
                overlap = cur.fetchone()[0]

                #Check if the overlap of a newly generated route is too high..
                if overlap <= max_overlap:
                    cur.execute("INSERT INTO result_table SELECT " + str(i) + " AS did, " + str(start_zone) + " AS start_zone, "
                            + str(end_zone) + " AS end_zone, lid, node, geom, cost, link_cost, start_node, end_node, \
                            path_seq, agg_cost, speed, fcn_class," + str(my) + " as my FROM temp_table2")
                    i = i + 1
                    nr_routes = nr_routes + 1
                    # print("HÄR ÄR VI")
                    overlap_count = 0
                else:
                    cur.execute(
                        "INSERT INTO result_table SELECT -1 AS did, " + str(start_zone) + " AS start_zone, "
                        + str(end_zone) + " AS end_zone, lid, node, geom, cost, link_cost, start_node, end_node, \
                                            path_seq, agg_cost, speed, fcn_class," + str(my) + " as my, 0.0 as time FROM temp_table2")

                cur.execute("DROP TABLE if exists temp_table1")
                cur.execute("SELECT * INTO temp_table1 from temp_table2")

                overlap_count += 1
                # if stuck in loop for close OD-pairs..
                if overlap_count > 50:
                    break
            else:
                break
        dummy = str(toc())
        cur.execute("UPDATE result_table SET time = " + dummy )
        cur.execute("INSERT INTO all_results SELECT * FROM result_table where did > -1")
        conn.commit()
        # No problems
        return 1
    # No route available
    if reverse is None:
        return 2
    # Only reverse cost available
    else:
        return 3


# Route set generation who returns some stats.
def routeSetGenerationStats(start_zone, end_zone, my, threshold):


    cur.execute("CREATE TABLE IF NOT EXISTS cost_table AS (select ST_Length(geom)/speed*3.6 AS link_cost, * \
    from model_graph)")
    cur.execute("CREATE TABLE IF NOT EXISTS all_results(did INT, start_zone INT, end_zone INT, lid BIGINT, node BIGINT, \
               geom geometry,cost double precision,link_cost DOUBLE PRECISION, start_node BIGINT, end_node BIGINT,path_seq INT,agg_cost DOUBLE PRECISION, \
               speed numeric, fcn_class BIGINT)")

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
    cur.execute("SELECT 1 AS did, " + str(start_zone) + " AS start_zone, " + str(end_zone) + " AS end_zone, lid, node, \
    geom, cost, link_cost,start_node, end_node, path_seq, agg_cost, speed, fcn_class INTO \
    result_table FROM temp_table1")

    # Getting total cost for route 1 and setting first stop criterion.
    cur.execute("SELECT sum(link_cost) FROM temp_table1")

    route1_cost = cur.fetchone()[0]
    #print("Current cost route 1: " + str(route1_cost))
    route_stop = route1_cost

    cur.execute("SELECT SUM(ST_LENGTH(geom)) as total_length FROM temp_table1")
    distance = cur.fetchone()[0]


    # # Pen cost as breaking if stuck instead of nr_routes
    # pen_q = db.exec_("SELECT SUM(cost) from temp_table1")
    # pen_q.next()
    # # print("Pencost för rutt: "+str(pen_q.value(0)))
    # pen_stop = pen_q.value(0)

    # Calculationg alternative routes
    i = 2
    nr_routes = 1
    avg_coveragekm = 0
    avg_coveragelid = 0
    avg_coveragekm_shortest = 0

    # while comp(route_stop, route1_cost, threshold):
    while True:
        #print("Route stop is ="+str(route_stop)+" and distance is ="+str(distance))
        if nr_routes >= 100 or route_stop is not None:
            print("Warning: The number of routes was over 100 for start zone: \
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

        # Normal penalty
        cur.execute("SELECT * INTO temp_table2 FROM pgr_dijkstra('SELECT id, source, target, \
        CASE WHEN pen.cost IS NULL THEN subq.cost ELSE pen.cost END AS cost, reverse_cost \
        FROM (SELECT lid AS id, start_node AS source, end_node AS target, link_cost AS cost, 1000 AS reverse_cost \
        FROM cost_table) AS subq LEFT JOIN \
            (select lid as edge, max(cost) + (max(cost)/(" + str(my) + " * " + str(route_stop) + "))*LN(" + str(delta) + ") AS cost \
        from result_table group by lid ) AS pen ON \
        (subq.id = pen.edge)'," + str(start) + "," + str(end) + ") INNER JOIN cost_table ON(edge = lid)")
        #

        # Penalty according to 9
        # cur.execute("SELECT * INTO temp_table2 FROM pgr_dijkstra('SELECT id, source, target, \
        #         CASE WHEN pen.cost IS NULL THEN subq.cost ELSE pen.cost END AS cost, reverse_cost \
        #         FROM (SELECT lid AS id, start_node AS source, end_node AS target, link_cost AS cost, 1000 AS reverse_cost \
        #         FROM cost_table) AS subq LEFT JOIN \
        #             (select lid as edge, max(cost) + " + str(my) + " * sqrt(" + str(route_stop) + ") AS cost \
        #         from result_table group by lid ) AS pen ON \
        #         (subq.id = pen.edge)'," + str(start) + "," + str(end) + ") INNER JOIN cost_table ON(edge = lid)")

        # Saving route cost without penalty and updating route_stop.
        cur.execute("SELECT SUM(cost_table.link_cost) AS tot_cost FROM temp_table2 \
        INNER JOIN cost_table ON cost_table.lid = temp_table2.lid;")
        route_stop = cur.fetchone()[0]

        #print("Current cost route " + str(i) + ": " + str(route_stop))

        # print("difference is = " + str(route_stop / route1_cost))

        # Saving route cost with penalty. Remove comment if  penalty want to be used as breaking criterion
        # pen_q = db.exec_("SELECT SUM(cost) from temp_table2")
        # pen_q.next()
        # # print("Pencost för rutt: "+str(pen_q.value(0)))
        # pen_stop = pen_q.value(0)


        if comp(route_stop, route1_cost, threshold):
            cur.execute("INSERT INTO result_table SELECT " + str(i) + " AS did, " + str(start_zone) + " AS start_zone, "
                        + str(end_zone) + " AS end_zone, lid, node, geom, cost, link_cost, start_node, end_node, \
                        path_seq, agg_cost, speed, fcn_class FROM temp_table2")

            # Coverage using the length coverage.
            cur.execute("SELECT sum(st_length(geom)) / (SELECT sum(st_length(geom)) FROM result_table WHERE \
                        did=" + str(
                i) + ")  AS per FROM (SELECT did,lid,geom FROM result_table WHERE did=" + str(i) + " and lid = \
                        ANY(SELECT lid FROM result_table WHERE NOT did >= " + str(
                i) + ") group by lid,did,geom) as foo")
            coveragekm = cur.fetchone()[0]
            print("rutt " + str(i) + " " + str(coveragekm) + " % längd av länkar överlappar!")

            # Coverage how similiar the routes are to the shortest route
            cur.execute("SELECT coalesce(sum(st_length(geom)) / (SELECT sum(st_length(geom)) FROM result_table \
            WHERE did="+str(i)+"),0)  AS per FROM (SELECT did,lid,geom FROM result_table \
            WHERE did="+str(i)+" and lid = ANY(SELECT lid FROM result_table \
            WHERE did = 1) group by lid,did,geom) as foo")
            coveragekmshortest = cur.fetchone()[0]
            #print("rutt " + str(i) + " " + str(coveragekmshortest) + " % länkar av länkar överlappar med kortaste vägen!")

            # cur.execute("SELECT SUM(ST_LENGTH(geom)) as total_length FROM temp_table2")
            # distance = cur.fetchone()[0]

            # Coverage using equal lids.
            cur.execute("SELECT cast(count(*) as float) / (SELECT COUNT(*) FROM result_table WHERE did=" + str(i) + ") AS per \
                        FROM (SELECT did,lid FROM result_table WHERE did=" + str(i) + " and lid = ANY(SELECT lid FROM result_table \
                        WHERE NOT did >= " + str(i) + ") group by lid,did) as foo")
            coveragelid = cur.fetchone()[0]
            #print("rutt " + str(i) + " " + str(coveragelid) + " lid länkar överlappar!")
            cur.execute("DROP TABLE if exists temp_table1")
            cur.execute("SELECT * INTO temp_table1 from temp_table2")
            i = i + 1
            nr_routes = nr_routes + 1
        else:
            break

        if coveragekm:
            avg_coveragekm += coveragekm
            avg_coveragelid += coveragelid
            #avg_coveragekm_shortest += coveragekmshortest

    cur.execute("INSERT INTO all_results SELECT * FROM result_table")
    conn.commit()


    if nr_routes > 1:
        resar = [nr_routes, avg_coveragekm / (nr_routes-1), avg_coveragelid / (nr_routes-1), avg_coveragekm_shortest / (nr_routes-1)]
        #print(resar)
        return resar
    else:
        return [nr_routes,-1]


def selectedODResultTable(start_list, end_list, my, threshold, removed_lids):

    nr_routes = []
    cur.execute("DROP TABLE if exists all_results")
    cur.execute("CREATE TABLE IF NOT EXISTS all_results(did INT, start_zone INT, end_zone INT, lid BIGINT, start_node \
               BIGINT, end_node BIGINT, \
               geom geometry,cost double precision,link_cost DOUBLE PRECISION,path_seq INT,agg_cost DOUBLE PRECISION, \
               speed numeric, fcn_class BIGINT)")

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
    cur.execute("CREATE TABLE IF NOT EXISTS all_results(did INT, start_zone INT, end_zone INT, lid BIGINT, start_node \
               BIGINT, end_node BIGINT, \
               geom geometry,cost double precision,link_cost DOUBLE PRECISION,path_seq INT,agg_cost DOUBLE PRECISION, \
               speed numeric, fcn_class BIGINT)")

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

# OBSERVE
def route_set_generation_rejoin(start_zone, end_zone, my, threshold):

    print("Rejoin IT UP! :")


    cur.execute("CREATE TABLE IF NOT EXISTS cost_table AS (select ST_Length(geom)/speed*3.6 AS link_cost, * \
    from model_graph)")
    cur.execute("CREATE TABLE IF NOT EXISTS all_results(did INT, start_zone INT, end_zone INT, lid BIGINT, start_node \
            BIGINT, end_node BIGINT, \
            geom geometry,cost double precision,link_cost DOUBLE PRECISION,path_seq INT,agg_cost DOUBLE PRECISION, \
            speed numeric, fcn_class BIGINT)")

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
    cur.execute("SELECT 1 AS did, " + str(start_zone) + " AS start_zone, " + str(end_zone) + " AS end_zone, lid, start_node, end_node, \
    geom, cost, link_cost, path_seq, agg_cost, speed, fcn_class, 0 as rejoin_link INTO \
    result_table FROM temp_table1")

    cur.execute("INSERT INTO result_table SELECT 1 AS did, " + str(start_zone) + " AS start_zone, " + str(end_zone) +
        " AS end_zone, a.lid, a.start_node, a.end_node, \
        a.geom, a.link_cost as cost, a.link_cost,b.path_seq, b.agg_cost, a.speed, a.fcn_class, 1 as rejoin_link  \
        FROM  cost_table AS a INNER JOIN result_table as b ON( \
		b.start_node=a.start_node or b.end_node = a.start_node or b.end_node=a.end_node \
		or b.start_node=a.end_node) \
		WHERE NOT EXISTS (SELECT * FROM result_table WHERE lid=a.lid)")


    # Getting total cost for route 1 and setting first stop criterion.
    cur.execute("SELECT sum(link_cost) FROM temp_table1")
    route1_cost = cur.fetchone()[0]
    #print("Current cost route 1: " + str(route1_cost))
    route_stop = route1_cost

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
        cur.execute("Select COUNT(*) from result_table")
        delta = cur.fetchone()[0]

        #print("DELTA VALUE IS =:"+str(delta))
        # Parameter

        # Route 2 penalty
        cur.execute("DROP TABLE if exists temp_table2")
        cur.execute("SELECT * INTO temp_table2 FROM pgr_dijkstra('SELECT id, source, target, \
        CASE WHEN pen.cost IS NULL THEN subq.cost ELSE pen.cost END AS cost, reverse_cost \
        FROM (SELECT lid AS id, start_node AS source, end_node AS target, link_cost AS cost, 10000 AS reverse_cost \
        FROM cost_table) AS subq LEFT JOIN \
             (select lid as edge, CASE WHEN rejoin_link=0 THEN max(cost) + (max(cost)/(" + str(my) + " * " +
                    str(route_stop) + "))*LN(" + str(delta) + ") ELSE max(cost)+max(cost)*0.5 END  AS cost \
        from result_table group by lid,rejoin_link) AS pen ON \
        (subq.id = pen.edge)'," + str(start) + "," + str(end) + ") INNER JOIN cost_table ON(edge = lid)")



        # Saving route cost without penalty and updating route_stop.
        cur.execute("SELECT SUM(cost_table.link_cost) AS tot_cost FROM temp_table2 \
        INNER JOIN cost_table ON cost_table.lid = temp_table2.lid;")
        route_stop = cur.fetchone()[0]

        #print("Current cost route " + str(i) + ": " + str(route_stop))

        # print("difference is = " + str(route_stop / route1_cost))

        # Saving route cost with penalty. Remove comment if  penalty want to be used as breaking criterion
        # pen_q = db.exec_("SELECT SUM(cost) from temp_table2")
        # pen_q.next()
        # print("Pencost för rutt: "+str(pen_q.value(0)))
        # pen_stop = pen_q.value(0)

        if comp(route_stop, route1_cost, threshold):

            cur.execute("INSERT INTO result_table SELECT " + str(i) + " AS did, " + str(start_zone) + " AS start_zone, "
                + str(end_zone) + " AS end_zone, lid, start_node, end_node, geom, cost, link_cost,path_seq, agg_cost, speed, fcn_class, \
                0 as rejoin_link FROM temp_table2")

            cur.execute("INSERT INTO result_table SELECT " + str(i) + " AS did, " + str(start_zone) + " AS start_zone, "
                + str(end_zone) + " AS end_zone, a.lid, a.start_node, a.end_node, a.geom, a.link_cost as cost, a.link_cost,\
                b.path_seq ,b.agg_cost, a.speed, a.fcn_class, 1 as rejoin_link FROM cost_table AS a INNER JOIN result_table as b ON( \
		        b.start_node=a.start_node or b.end_node = a.start_node or b.end_node=a.end_node \
		        or b.start_node=a.end_node) \
		        WHERE NOT EXISTS (SELECT * FROM result_table WHERE lid=a.lid)")

            # Coverage calculation here.

            cur.execute("SELECT sum(st_length(geom)) / (SELECT sum(st_length(geom)) FROM result_table WHERE \
                did="+str(i)+" and rejoin_link = 0)  AS per FROM (SELECT did,lid,geom FROM result_table WHERE did="+str(i)+" and lid = \
                ANY(SELECT lid FROM result_table WHERE NOT did >= "+str(i)+") group by lid,did,geom) as foo")
            coverage = cur.fetchone()
            #print("rutt " + str(i) + " " + str(coverage) + " länkar överlappar!")

            cur.execute("DROP TABLE if exists temp_table1")
            cur.execute("SELECT * INTO temp_table1 from temp_table2")

            i = i + 1
            nr_routes = nr_routes + 1
        else:
            break

    cur.execute("INSERT INTO all_results SELECT did, start_zone, end_zone, lid, start_node, end_node, geom, cost, link_cost, path_seq,agg_cost, speed, fcn_class lid FROM result_table")
    conn.commit()
    #print("all results inserted")

    return nr_routes

#Similar to routeSetGeneration, reuturns overlap
def overlapDifferentMy(start_zone, end_zone, my, threshold):

    cur.execute("CREATE TABLE IF NOT EXISTS cost_table AS (select ST_Length(geom)/speed*3.6 AS link_cost, * \
        from model_graph)")
    cur.execute("CREATE TABLE IF NOT EXISTS all_results(start_zone INT, end_zone INT,did INT, seq INT, path_seq INT, \
            node BIGINT,edge BIGINT,cost DOUBLE PRECISION,agg_cost DOUBLE PRECISION, \
            link_cost DOUBLE PRECISION, id INT, geom GEOMETRY, lid BIGINT, start_node BIGINT, \
            end_node BIGINT,ref_lids CHARACTER VARYING,ordering CHARACTER VARYING, \
            speed NUMERIC, lanes BIGINT, fcn_class BIGINT, internal CHARACTER VARYING)")

    cur.execute("CREATE TABLE IF NOT EXISTS all_results(start_zone INT, end_zone INT,did INT, seq INT, path_seq INT, \
            node BIGINT,edge BIGINT,cost DOUBLE PRECISION,agg_cost DOUBLE PRECISION, \
            link_cost DOUBLE PRECISION, id INT, geom GEOMETRY, lid BIGINT, start_node BIGINT, \
            end_node BIGINT,ref_lids CHARACTER VARYING,ordering CHARACTER VARYING, \
            speed NUMERIC, lanes BIGINT, fcn_class BIGINT, internal CHARACTER VARYING)")

    start = genonenode(start_zone)
    end = genonenode(end_zone)

    # print("Start node is: "+str(start)+" End node is: "+str(end))

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
    # print("Current cost route 1: " + str(route1_cost))
    route_stop = route1_cost

    # # Pen cost as breaking if stuck instead of nr_routes
    # pen_q = db.exec_("SELECT SUM(cost) from temp_table1")
    # pen_q.next()
    # # print("Pencost för rutt: "+str(pen_q.value(0)))
    # pen_stop = pen_q.value(0)

    # Calculationg alternative routes
    i = 2
    nr_routes = 1
    sum_overlap = 0
    # while comp(route_stop, route1_cost, threshold):
    while True:
        if nr_routes >= 50:
            print("Warning: The number of routes was over 10 for start zone: \
                 " + str(start_zone) + " and end zone: " + str(end_zone))
            break

        # Calculating penalizing term (P. 14 in thesis work)
        # Delta value
        cur.execute("Select COUNT(*) from result_table")
        delta = cur.fetchone()[0]

        # print("DELTA VALUE IS =:"+str(delta))
        # Parameter

        # Route 2
        cur.execute("DROP TABLE if exists temp_table2")
        cur.execute("SELECT * INTO temp_table2 FROM pgr_dijkstra('SELECT id, source, target, \
            CASE WHEN pen.cost IS NULL THEN subq.cost ELSE pen.cost END AS cost, reverse_cost \
            FROM (SELECT lid AS id, start_node AS source, end_node AS target, link_cost AS cost, 1000 AS reverse_cost \
            FROM cost_table) AS subq LEFT JOIN \
                (select lid as edge, max(cost) + (max(cost)/(" + str(my) + " * "+str(route_stop)+"))*LN(" + str(delta) + ") AS cost \
            from result_table group by lid ) AS pen ON \
            (subq.id = pen.edge)'," + str(start) + "," + str(end) + ") INNER JOIN cost_table ON(edge = lid)")

        # Saving route cost without penalty and updating route_stop.
        cur.execute("SELECT SUM(cost_table.link_cost) AS tot_cost FROM temp_table2 \
            INNER JOIN cost_table ON cost_table.lid = temp_table2.lid;")
        route_stop = cur.fetchone()[0]
        # print("Current cost route " + str(i) + ": " + str(cost_q.value(0)))

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
            cur.execute(
                "SELECT sum(st_length(geom)) / (SELECT sum(st_length(geom)) FROM result_table WHERE did=" + str(i) + ") AS per \
                FROM (SELECT did,lid,geom FROM result_table WHERE did=" + str(i) + " and lid = ANY(SELECT lid FROM result_table \
                WHERE NOT did >= " + str(i) + ") group by lid,did,geom) as foo")
            coverage = cur.fetchone()[0]
            #print("rutt " + str(i) + " " + str(distance) + " länk-km överlappar!")

            cur.execute("DROP TABLE if exists temp_table1")
            cur.execute("SELECT * INTO temp_table1 from temp_table2")
            i = i + 1
            nr_routes = nr_routes + 1
        else:
            break
        if coverage:
            sum_overlap += coverage

    cur.execute("INSERT INTO all_results SELECT * FROM result_table")
    # print("all results inserted")
    if nr_routes > 1:
        return sum_overlap/(nr_routes-1)
    else:
        return 0

def rejoinOverlapDifferentMy(start_zone, end_zone, my, threshold, range):
    #print("TUBE IT UP! :" + str(range))

    cur.execute("CREATE TABLE IF NOT EXISTS cost_table AS (select ST_Length(geom)/speed*3.6 AS link_cost, * \
        from model_graph)")
    cur.execute("CREATE TABLE IF NOT EXISTS all_results(did INT, start_zone INT, end_zone INT, lid BIGINT, start_node \
                BIGINT, end_node BIGINT, \
                geom geometry,cost double precision,link_cost DOUBLE PRECISION,path_seq INT,agg_cost DOUBLE PRECISION, \
                speed numeric, fcn_class BIGINT)")

    start = genonenode(start_zone)
    end = genonenode(end_zone)

    # print("Start node is: "+str(start)+" End node is: "+str(end))

    cur.execute("DROP TABLE if exists temp_table1")
    # Route 1
    cur.execute("SELECT * INTO temp_table1 from pgr_dijkstra('SELECT lid AS id, start_node AS source, end_node AS target, \
         link_cost AS cost, 1000 AS reverse_cost FROM cost_table'," + str(start) + "," + str(end) + ") \
         INNER JOIN cost_table ON(edge = lid)")

    # Result table creating
    cur.execute("DROP TABLE if exists result_table")
    cur.execute("SELECT 1 AS did, " + str(start_zone) + " AS start_zone, " + str(end_zone) + " AS end_zone, lid, start_node, end_node, \
        geom, cost, link_cost, path_seq, agg_cost, speed, fcn_class, 0 as rejoin_link INTO \
        result_table FROM temp_table1")

    cur.execute("INSERT INTO result_table SELECT 1 AS did, " + str(start_zone) + " AS start_zone, " + str(end_zone) +
                " AS end_zone, a.lid, a.start_node, a.end_node, \
                a.geom, a.link_cost as cost, a.link_cost,b.path_seq, b.agg_cost, a.speed, a.fcn_class, 1 as rejoin_link  \
                FROM  cost_table AS a INNER JOIN result_table as b ON( \
                b.start_node=a.start_node or b.end_node = a.start_node or b.end_node=a.end_node \
                or b.start_node=a.end_node) \
                WHERE NOT EXISTS (SELECT * FROM result_table WHERE lid=a.lid)")

    # Getting total cost for route 1 and setting first stop criterion.
    cur.execute("SELECT sum(link_cost) FROM temp_table1")
    route1_cost = cur.fetchone()[0]
    #print("Current cost route 1: " + str(route1_cost))
    route_stop = route1_cost

    # # Pen cost as breaking if stuck instead of nr_routes
    # pen_q = db.exec_("SELECT SUM(cost) from temp_table1")
    # pen_q.next()
    # # print("Pencost för rutt: "+str(pen_q.value(0)))
    # pen_stop = pen_q.value(0)

    # Calculationg alternative routes
    i = 2
    nr_routes = 1
    sum_overlap = 0
    # while comp(route_stop, route1_cost, threshold):
    while True:
        if nr_routes >= 10:
            print("Warning: The number of routes was over 10 for start zone: \
                " + str(start_zone) + " and end zone: " + str(end_zone))
            break

        # Calculating penalizing term (P. 14 in thesis work)
        # Delta value
        cur.execute("Select COUNT(*) from result_table")
        delta = cur.fetchone()[0]

        # print("DELTA VALUE IS =:"+str(delta))
        # Parameter

        # Route 2 penalty
        cur.execute("DROP TABLE if exists temp_table2")
        cur.execute("SELECT * INTO temp_table2 FROM pgr_dijkstra('SELECT id, source, target, \
            CASE WHEN pen.cost IS NULL THEN subq.cost ELSE pen.cost END AS cost, reverse_cost \
            FROM (SELECT lid AS id, start_node AS source, end_node AS target, link_cost AS cost, 10000 AS reverse_cost \
            FROM cost_table) AS subq LEFT JOIN \
                 (select lid as edge, CASE WHEN rejoin_link=0 THEN max(cost) + (max(cost)/(" + str(my) + " * " + str(
            route_stop) + "))*LN(" + str(delta) + ") ELSE max(cost)+max(cost)*0.5 END  AS cost \
            from result_table group by lid,rejoin_link) AS pen ON \
            (subq.id = pen.edge)'," + str(start) + "," + str(end) + ") INNER JOIN cost_table ON(edge = lid)")

        # Saving route cost without penalty and updating route_stop.
        cur.execute("SELECT SUM(cost_table.link_cost) AS tot_cost FROM temp_table2 \
            INNER JOIN cost_table ON cost_table.lid = temp_table2.lid;")
        route_stop = cur.fetchone()[0]

        #print("Current cost route " + str(i) + ": " + str(route_stop))

        # print("difference is = " + str(route_stop / route1_cost))

        # Saving route cost with penalty. Remove comment if  penalty want to be used as breaking criterion
        # pen_q = db.exec_("SELECT SUM(cost) from temp_table2")
        # pen_q.next()
        # print("Pencost för rutt: "+str(pen_q.value(0)))
        # pen_stop = pen_q.value(0)

        if comp(route_stop, route1_cost, threshold):

            cur.execute("INSERT INTO result_table SELECT " + str(i) + " AS did, " + str(start_zone) + " AS start_zone, "
                        + str(end_zone) + " AS end_zone, lid, start_node, end_node, geom, cost, link_cost,path_seq, agg_cost, speed, fcn_class, \
                    0 as rejoin_link FROM temp_table2")

            cur.execute("INSERT INTO result_table SELECT " + str(i) + " AS did, " + str(start_zone) + " AS start_zone, "
                        + str(end_zone) + " AS end_zone, a.lid, a.start_node, a.end_node, a.geom, a.link_cost as cost, a.link_cost,\
                    b.path_seq ,b.agg_cost, a.speed, a.fcn_class, 1 as rejoin_link FROM cost_table AS a INNER JOIN result_table as b ON( \
    		        b.start_node=a.start_node or b.end_node = a.start_node or b.end_node=a.end_node \
    		        or b.start_node=a.end_node) \
    		        WHERE NOT EXISTS (SELECT * FROM result_table WHERE lid=a.lid)")

            # Coverage calculation here.

            cur.execute("SELECT sum(st_length(geom)) / (SELECT sum(st_length(geom)) FROM result_table WHERE \
                did=" + str(
                i) + " and rejoin_link = 0)  AS per FROM (SELECT did,lid,geom FROM result_table WHERE did=" + str(i) + " and lid = \
                ANY(SELECT lid FROM result_table WHERE NOT did >= " + str(i) + ") group by lid,did,geom) as foo")
            coverage = cur.fetchone()[0]
            #print("rutt " + str(i) + " " + str(coverage) + " länkar överlappar!")

            cur.execute("DROP TABLE if exists temp_table1")
            cur.execute("SELECT * INTO temp_table1 from temp_table2")

            i = i + 1
            nr_routes = nr_routes + 1
        else:
            break
        if coverage:
            sum_overlap += coverage

    cur.execute(
            "INSERT INTO all_results SELECT did, start_zone, end_zone, lid, start_node, end_node, geom, cost, link_cost, path_seq,agg_cost, speed, fcn_class lid FROM result_table")
    conn.commit()
    # print("all results inserted")
    if nr_routes > 1:
        return sum_overlap / (nr_routes - 1)
    else:
        return 0

def excelStats(start_list, end_list, my_list, threshold, rejoin):

    cur.execute("DROP TABLE if exists all_results")
    #Overlap
    # j = 0
    # while j < len(my_list):
    #     tic()
    #     i = 0
    #     sum_overlap = 0
    #     while i < len(start_list):
    #         print("i är : " + str(i))
    #         if rejoin == 1:
    #             sum_overlap += rejoinOverlapDifferentMy(start_list[i], end_list[i], my_list[j], threshold, 1)
    #         else:
    #             sum_overlap += OverlapDifferentMy(start_list[i], end_list[i], my_list[j], threshold)
    #         # print(str(sum_overlap))
    #         i += 1
    #     print("my är: " + str(my_list[j]) +  " med overlap: " + str(sum_overlap / i))
    #     j += 1
    #     toc()
    # cur.execute("DROP TABLE if exists all_results")

    # Nr routes

    j = 0
    while j < len(my_list):
        i = 0
        sum_nr_routes = 0
        coveragekm = 0.0
        coveragelid = 0.0
        coveragekm_shortest = 0.0
        counter=0
        while i < len(start_list):
            # print("i är : " + str(i))
            if rejoin == 1:
                sum_nr_routes += route_set_generation_rejoin(start_list[i], end_list[i], my_list[j], threshold, range)
            else:
                res_arr = []
                res_arr = routeSetGenerationStats(start_list[i], end_list[i], my_list[j], threshold)
                #print("nr routes:"+str(res_arr[0])+" coverage:"+str(res_arr[1]))
                sum_nr_routes += res_arr[0]
                if res_arr[1] > 0 and res_arr[2] > 0:
                    coveragekm += res_arr[1]
                    coveragelid += res_arr[2]
                    coveragekm_shortest += res_arr[3]
                    counter = counter+1
            # print(str(sum_overlap))
            i += 1
        if counter > 0:
            print("my är: " + str(my_list[j]) + " med avg nr routes: " + str(sum_nr_routes / i)+ ", average coverage i km: "
                  +str(coveragekm/counter) + " och average coverage i länkar " + str(coveragelid/counter) +
                  " coverage against shortest path is :" + str(coveragekm_shortest/counter) + " antal rutter med bara 1 rutt är :"+str(counter))
        else:
            print(sum_nr_routes/i)

        j += 1

# Generate route sets between start_list and end_list for differnet my values from my_list
def populate_all_res(start_list,end_list,my_list,threshold, max_overlap):

    print("Generating all_results table")
    cur.execute("DROP TABLE if exists all_results")

    j = 0
    while j < len(my_list):
        i = 0
        kvot = 10
        progress = len(start_list) / kvot
        prog_count = kvot
        while i < len(start_list):
            if i >= progress:
                print(""+ str(prog_count) + "% delprocess klar... ")
                prog_count = prog_count + kvot
                progress = progress + len(start_list)/kvot

            try:
                routeSetGeneration(start_list[i], end_list[i], my_list[j], threshold, max_overlap)
            except:  # catch *all* exceptions
                print("Route set generation failed..")

            i += 1
        j += 1

        # datetime object containing current date and time
        now = datetime.now()
        # dd/mm/YY H:M:S
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
        print(""+ str(j*100/len(my_list)) + "%  klart and time is: " +  dt_string)

    # Index creation on all_result table
    cur.execute("CREATE INDEX all_res_geom_idx ON all_results USING GIST (geom)")
    cur.execute("CREATE INDEX all_res_id_idx on all_results (lid)")
    cur.execute("CREATE INDEX all_res_start_end_idx on all_results (start_zone, end_zone)")
    cur.execute("CREATE INDEX all_res_start_end_my_idx on all_results (start_zone, end_zone,my)")
    cur.execute("CREATE INDEX did_idx on all_results (did)")
    conn.commit()
    print("table all_results FINISHED!")

# Insert average values into my_od_res from all_results
def getAveragesOD():
    print("STARTING TO GENERATE AVERAGES")
    cur.execute("DROP TABLE if exists my_od_res")
    cur.execute("CREATE TABLE my_od_res(start_zone BIGINT, end_zone BIGINT, my DOUBLE PRECISION, nr_routes BIGINT,\
     avg_cov_km DOUBLE PRECISION, avg_cov_lid DOUBLE PRECISION, avg_cov_mlkm DOUBLE PRECISION, \
     avg_cov_srkm DOUBLE PRECISION, sr_cost DOUBLE PRECISION, avg_cost DOUBLE PRECISION, time DOUBLE PRECISION)")

    # Get od-pairs
    cur.execute("SELECT DISTINCT start_zone, end_zone FROM all_results")
    all_od = cur.fetchall()

    # Get my:s
    cur.execute("SELECT DISTINCT my FROM all_results")
    all_my = cur.fetchall()


    # Loop for my
    for my in all_my:
        print("my",my[0])

        # Loop for od-pairs
        for od in all_od:

            print("start", od[0])
            # print("end", od[1])
            # Variables to be inserted in the OD-pairs row
            avg_coveragekm = 0.0
            avg_coveragelid = 0.0
            avg_coveragemlkm = 0.0
            avg_coveragesrkm = 0.0
            nr_routes = 0.0
            avg_cost = 0.0
            shortest_route = 0.0
            time = 0.0

            # Nr routes for OD-pair.
            cur.execute("select max(did) as nr_routes from all_results WHERE my=" + str(my[0]) + " and start_zone="
            + str(od[0]) + " and end_zone=" + str(od[1]))
            nr_routes = float(cur.fetchone()[0])
            #print(" nr of routes : "+str(nr_routes))

            # Shortest path each OD-pair
            cur.execute("SELECT agg_cost FROM all_results WHERE did=1 and start_zone = " + str(od[0]) + " and end_zone = " + str(od[1]) + " and \
            my=" + str(my[0]) + " and path_seq = (SELECT max(path_seq) from all_results WHERE did=1 and start_zone = " + str(od[0]) + " and \
            end_zone = " + str(od[1]) + " and my =" + str(my[0]) + " )")
            shortest_route = cur.fetchone()[0]
            #
            # Average route cost in OD-pair
            temp_cost =0.0
            for x in range(1,int(nr_routes)+1):
                #print("räknar jag rätt?",str(x))
                cur.execute("SELECT sum(link_cost) FROM all_results WHERE did=" + str(x) + " and start_zone = " + str(
                    od[0]) + " and end_zone = " + str(od[1]) + " and \
                    my=" + str(my[0]))
                temp_cost += cur.fetchone()[0]
                # print("temp cost is:", temp_cost)
            avg_cost = temp_cost/nr_routes
            # #print("blir det rätt?", avg_cost)

            # # Average cover in length of routes in od-pair.
            #
            # if nr_routes > 1:
            #     i = nr_routes
            #     coveragekm = 0.0
            #     while i > 1:
            #         cur.execute("SELECT coalesce(sum(st_length(geom)) / (SELECT sum(st_length(geom)) FROM all_results WHERE \
            #                     did=" + str(i) +" and start_zone = " + str(od[0]) + " and end_zone=" + str(od[1]) + "\
            #                     and my = " + str(my[0]) + "),0) AS per FROM (SELECT did,lid,geom FROM all_results WHERE \
            #                     did=" + str(i) + " and start_zone = " + str(od[0]) + " and end_zone=" + str(od[1]) + "\
            #                     and my = " + str(my[0]) + " and lid = \
            #                     ANY(SELECT lid FROM all_results WHERE start_zone = " + str(od[0]) + " and end_zone=" + str(od[1]) + "\
            #                     and my = " + str(my[0]) + " and NOT did >= " + str(i) + ") group by lid,did,geom)\
            #                                         as foo")
            #
            #         current = cur.fetchone()[0]
            #         #print("current coverage :"+str(current))
            #         coveragekm += current
            #         i -= 1
            #     avg_coveragekm = coveragekm/(nr_routes-1)
            #     #print("Coverage using length is :", coveragekm / (nr_routes - 1))
            # else:
            #     avg_coveragekm = -1
                #print("Only 1 route generated!")
            #

            #Average cover in lids for routes in od-pair.
            #

            # if nr_routes > 1:
            #     i = nr_routes
            #     coveragelid = 0.0
            #     while i > 1:
            #         cur.execute("SELECT cast(count(*) as float) / (SELECT COUNT(*) FROM all_results WHERE did=" + str(i) + " and my=" + str(my[0]) + ") AS per \
            #                                 FROM (SELECT did,lid FROM all_results WHERE did=" + str(i) + " and lid = ANY(SELECT lid FROM all_results \
            #                                 WHERE NOT did >= " + str(i) + ") group by lid,did) as foo")
            #         current = cur.fetchone()[0]
            #         coveragelid += current
            #
            #         i -= 1
            #     avg_coveragelid = coveragelid/(nr_routes-1)
            #     #print("Coverage using lids is :", coveragelid/(nr_routes-1))
            # else:
            #     avg_coveragelid = -1
                # print("Only 1 route generated!")

            # # Average cover using the most alike route in od-pair using length as comparison as coverage
            # #
            if nr_routes > 1:
                i = nr_routes
                coveragemlkm = 0.0
                while i > 1:
                    most_like = 0.0
                    j = nr_routes
                    while j > 0:
                        #print("j is: "+str(j)+"  i is: "+str(i))
                        if j != i:
                            cur.execute("SELECT coalesce(sum(st_length(geom)) / (SELECT sum(st_length(geom)) FROM all_results WHERE \
                                                            did=" + str(i) + " and start_zone = " + str(
                                od[0]) + " and end_zone=" + str(od[1]) + "\
                                                            and my = " + str(my[0]) + "),0) AS per FROM (SELECT did,lid,geom FROM all_results WHERE \
                                                            did=" + str(i) + " and start_zone = " + str(
                                od[0]) + " and end_zone=" + str(od[1]) + "\
                                                            and my = " + str(my[0]) + " and lid = \
                                                            ANY(SELECT lid FROM all_results WHERE did = " + str(j) + ") group by lid,did,geom)\
                                                                                as foo")
                            temp_ml = cur.fetchone()[0]
                            #print("overlap is:",temp_ml)


                            if (temp_ml > most_like):
                                most_like = temp_ml



                        j -= 1
                    #print("Most like for did="+str(i)+" is:", most_like)
                    coveragemlkm += most_like
                    i -= 1
                avg_coveragemlkm = coveragemlkm / (nr_routes - 1)
                #print("Coverage using most like length is :", coveragemlkm / (nr_routes - 1))
            else:
                avg_coveragemlkm = -1
                #print("Only 1 route generated!")


            # Time for OD-pair

            cur.execute("SELECT time from all_results where start_zone = " + str(od[0]) + " and end_zone="
                        + str(od[1]) + " and my = " + str(my[0]) + " group by start_zone, end_zone, my,time")
            time = cur.fetchone()[0]

            # Average cover to shorest using km.
            # if nr_routes >1:
            #     i = nr_routes
            #     coveragesrkm = 0.0
            #     while i > 1:
            #         cur.execute("SELECT coalesce(sum(st_length(geom)) / (SELECT sum(st_length(geom)) FROM all_results \
            #                                     WHERE did=" + str(i) + " and start_zone = " + str(od[0]) + " and end_zone=" + str(od[1]) + "and my = " + str(my[0]) +"),0)  AS per FROM (SELECT did,lid,geom FROM all_results \
            #                                     WHERE did=" + str(i) + " and start_zone = " + str(od[0]) + " and end_zone=" + str(od[1]) + "and my = " + str(my[0]) +" and lid = ANY(SELECT lid FROM all_results \
            #                                     WHERE did = 1) group by lid,did,geom) as foo")
            #         current = cur.fetchone()[0]
            #         #print("current coverage shorest =",current)
            #         coveragesrkm += current
            #
            #         i -= 1
            #     avg_coveragesrkm = coveragesrkm / (nr_routes - 1)
            #     #print("Coverage using shortest is :", avg_coveragesrkm)
            # else:
            #     avg_coveragesrkm = -1
            #     #print("Only 1 route generated")
            #

            #print("Add this to the database start = " + str(od[0]) + " end = " + str(od[1]) + " avg_ckm = "+str(avg_coveragekm)+" avg_clid = "+str(avg_coveragelid)+" avg_mlkm = "+str(avg_coveragemlkm) )
            #print("avg covrage against shorest",avg_coveragesrkm)
            #print("shortest route is :", shorest_route)
            # print("Inserting OD pair:", counter_done)
            cur.execute("INSERT INTO my_od_res SELECT " + str(od[0]) + " AS start_zone, " + str(od[1]) + " AS start_zone, "
                        + str(my[0]) + " AS my, " + str(nr_routes) + " AS nr_routes, " + str(avg_coveragekm) +
                        " AS avg_cov_km, " + str(avg_coveragelid) + " AS avg_cov_lid," + str(avg_coveragemlkm) +
                        " AS avg_cov_mlkm, " + str(avg_coveragesrkm) + " AS avg_cov_srkm, " + str(shortest_route) +
                        " AS sr_cost, " + str(avg_cost) + " AS avg_cost, " + str(time) + "AS time")

# Average of averages for each my value.
def getAllAverages(my_list):

    average_nr = []
    average_cov_km = []
    average_cost = []
    average_sr_cost = []
    average_mlkm = []
    average_cov_lid = []
    average_time = []
    for x in my_list:
        cur.execute("SELECT AVG(nr_routes) FROM my_od_res WHERE my = " + str(x))
        average_nr.append(cur.fetchone()[0])
        cur.execute("SELECT AVG(avg_cov_km) FROM my_od_res WHERE my = " + str(x)+" and avg_cov_km >= 0")
        average_cov_km.append(cur.fetchone()[0])
        cur.execute("SELECT AVG(avg_cost) FROM my_od_res WHERE my = " + str(x))
        average_cost.append(cur.fetchone()[0])
        cur.execute("SELECT AVG(sr_cost) FROM my_od_res WHERE my = " + str(x) )
        average_sr_cost.append(cur.fetchone()[0])
        cur.execute("SELECT AVG(avg_cov_mlkm) FROM my_od_res WHERE my = " + str(x) +" and avg_cov_mlkm >= 0")
        average_mlkm.append(cur.fetchone()[0])
        cur.execute("SELECT AVG(avg_cov_lid) FROM my_od_res WHERE my = " + str(x) + " and avg_cov_lid >= 0")
        average_cov_lid.append(cur.fetchone()[0])
        cur.execute("SELECT AVG(time) FROM my_od_res WHERE my = " + str(x) + " and avg_cov_lid >= 0")
        average_time.append(cur.fetchone()[0])

    return average_nr, average_cov_km, average_mlkm, average_cov_lid, average_cost, average_sr_cost,average_time

def generateRandomOd():
    cur.execute("DROP TABLE IF EXISTS rand_od")
    cur.execute("CREATE TABLE rand_od AS SELECT * FROM od_lid ORDER BY RANDOM()")
    cur.execute("ALTER TABLE rand_od ADD rand_id serial")
    cur.execute("SELECT * FROM rand_od")
    dummy = cur.fetchall()
    start_list = []
    end_list = []
    size = len(dummy)
    counter = 0
    for x in dummy:
        if counter >= size/2:
            start_list.append(x[1])
        else:
            end_list.append(x[1])
        counter += 1
    return start_list,end_list

def fetch_update(my, threshold, max_overlap, limit):
    mac = get_mac()

    #Check if any assignments needs to be finished
    cur.execute("SELECT origin, destination FROM all_od_pairs WHERE status = "+str(mac))
    assignment = cur.fetchall()
    #print("assignment: "+str(assignment))

    if not assignment:
        print("gick den in?")
        cur.execute("WITH cte AS (select * from all_od_pairs "
                    "where (EXTRACT(EPOCH FROM (NOW() - time_updated)) > 1 or time_updated IS NULL) and status = -1 limit "+str(limit)+") "
                    "UPDATE all_od_pairs a SET status = "+str(mac)+", time_updated = NOW() FROM cte WHERE  cte.id = a.id;")

        cur.execute("SELECT origin, destination FROM all_od_pairs WHERE status = "+str(mac))
        assignment = cur.fetchall()

    # print(len(assignment))
    # print(assignment)
    i = 0
    while i < len(assignment):
        if routeSetGeneration(assignment[i][0], assignment[i][1], my, threshold, max_overlap) == 1:
            cur.execute("UPDATE all_od_pairs SET status=1 WHERE origin = " +str(assignment[i][0])+ " and destination = " +str(assignment[i][1]))
        elif routeSetGeneration(assignment[i][0], assignment[i][1], my, threshold, max_overlap) == 2:
            cur.execute("UPDATE all_od_pairs SET status=2 WHERE origin = " + str(assignment[i][0]) + " and destination = " + str(assignment[i][1]))
        else:
            cur.execute("UPDATE all_od_pairs SET status=3 WHERE origin = " +str(assignment[i][0])+ " and destination = " +str(assignment[i][1]))

        cur.execute("UPDATE all_od_pairs SET time_updated=NOW() WHERE origin = " + str(assignment[i][0]) + " and destination = " + str(assignment[i][1]))
        i +=1

    conn.commit()
# End of function definitions

# Connection global to be used everywhere.
conn = psycopg2.connect(host="localhost", database="exjobb", user="postgres", password="password123")
conn.autocommit = True
cur = conn.cursor()


def main():
    tic()

    # Variable definitions
    my = 0.01
    threshold = 1.3
    max_overlap  = 0.8

    # Which zones to route between
    # TESTA om alla dör där 7704 7700 7701 7763 denna har väldigt liten del model_graph 7702
    start = 7852  # 7183
    end = 7987 # 7543

    cur.execute("DROP TABLE if exists all_results")
    cur.execute("UPDATE all_od_pairs SET status = -1")
    cur.execute("UPDATE all_od_pairs SET time_updated  = null")

    #routeSetGeneration(7088, 7401, my, threshold, max_overlap)
    fetch_update(my, threshold, max_overlap,100)

    start_zone = 7815
    end_zone = 7798

    # cur.execute("DROP TABLE if exists all_results")
    # cur.execute("DROP TABLE if exists cost_table")
    # cur.execute("DROP TABLE if exists od_lid")

    #routeSetGeneration(start_zone, end_zone, my, threshold, max_overlap)



    # Korta OD-par
    start_list = [7143, 7603, 7412, 6904, 6970, 7190, 6893, 7551, 7894, 7852, 7223, 7328, 7648]
    end_list = [6820, 7585, 7635, 6870, 6937, 7170, 7161, 7539, 7886, 7946, 6973, 7308, 7661]


    # Långa OD-par
    start_list = [7472, 7815, 7128, 7801, 7707, 7509, 7304, 7151, 7487, 7737]
    end_list = [7556, 7635, 6912, 7603, 6976, 7174, 7680, 7053, 7282, 6822]

    all_list = [8005, 7195, 6884, 6837, 6776, 7835, 7864, 6955, 7570, 7422, 7680, 7557, 7560, 6879, 6816, 7630, 7162,
                7187, 7227]
    smaller_list = [8005, 7195, 6884, 6837, 6776]

    # Which lids to remove
    removed_lid = [89227]  # Götgatan, [83025] för Söderledstunneln
    # removed_lids = [83025, 84145] # [81488, 83171] för Essingeleden, [83025, 84145] för Söderleden

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


    #routeSetGeneration(start, end, my, threshold, max_overlap)

    #onetoMany(6904)
    #my_list = [0.001, 0.003,0.005, 0.01, 0.02, 0.03,0.05]

    start_list = [7472, 7815, 7128, 7801, 7707, 7509, 7304, 7151, 7487, 7737]
    end_list = [7556, 7556, 6912, 7603, 6976, 7174, 7680, 7053, 7282, 6822]
    start_list = [7472, 7472, 7472]
    end_list = [7556, 6912, 6822]
    ## AVERAGES TEST
    my_list = [0.001, 0.005, 0.01, 0.02, 0.03, 0.05]
    #my_list = [0.001, 0.01, 0.005]
    randomlist = []

    # start_list = generateRandomOd()[0]
    # end_list = generateRandomOd()[1]
    #


    # Generate all results
    # populate_all_res(start_list, end_list,my_list,threshold, max_overlap)

    #excelStats(start_list, end_list,my_list,threshold,0)

    # Gen avg od result creates table my_od_res
    #
    # getAveragesOD()

    #
    # # Gen average for all od-pairs
    # getAllAverages(my_list)
    # print("Average nr routes is :" + str(getAllAverages(my_list)[0]))
    # print("Average coverage km is :" + str(getAllAverages(my_list)[1]))
    # print("Average most like coverage :" + str(getAllAverages(my_list)[2]))
    # print("Average lid coverage :" + str(getAllAverages(my_list)[3]))
    # print("Average cost is :" + str(getAllAverages(my_list)[4]))
    # print("Average shorest routes is :" + str(getAllAverages(my_list)[5]))
    # print("Average time is :" + str(getAllAverages(my_list)[6]))


    #rejoin = 0 # = 1 if rejoin
    #excelStats(start_list, end_list, my_list, threshold,rejoin)

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
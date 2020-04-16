# Authors: Mattias Tunholm
# Date of creation: 2020-02-20

# Imports
import time
import sys
from datetime import datetime
import psycopg2
import numpy as np
from io import StringIO

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
               speed numeric, fcn_class BIGINT)")

    start = genonenode(start_zone)
    end = genonenode(end_zone)
    # print("Start zone is:"+str(start_zone))
    # print("End zone is:"+str(end_zone))
    # print("Start node is: "+str(start)+" End node is: "+str(end))

    cur.execute("DROP TABLE if exists temp_table1")
    # Route 1
    cur.execute("SELECT * INTO temp_table1 from pgr_dijkstra('SELECT lid AS id, start_node AS source, end_node AS target, \
     link_cost AS cost FROM cost_table'," + str(start) + "," + str(end) + ") \
     INNER JOIN cost_table ON(edge = lid)")



    # Getting total cost for route 1 and setting first stop criterion.
    cur.execute("SELECT sum(link_cost) FROM temp_table1")

    route1_cost = cur.fetchone()[0]
    # print("Current cost route 1: " + str(route1_cost))
    route_stop = route1_cost


    # Result table creating
    if route_stop is None:
        # print("No route BEFORE WHILE LOOP")
        cur.execute("DROP TABLE if exists result_table")

    else:
        cur.execute("DROP TABLE if exists result_table")
        cur.execute("SELECT 1 AS did, " + str(start_zone) + " AS start_zone, " + str(end_zone) + " AS end_zone, lid, node, \
        geom, cost, link_cost,start_node, end_node, path_seq, agg_cost, speed, fcn_class INTO \
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
                        print("Warning unusually high cost used in the while loop")
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
            CASE WHEN pen.cost IS NULL THEN subq.cost ELSE pen.cost END AS cost \
            FROM (SELECT lid AS id, start_node AS source, end_node AS target, link_cost AS cost \
            FROM cost_table) AS subq LEFT JOIN \
                (select lid as edge, max(cost) + (max(cost)/(" + str(my) + " * " + str(route_stop) + "))*LN(" + str(delta) + ") AS cost \
            from result_table group by lid ) AS pen ON \
            (subq.id = pen.edge)'," + str(start) + "," + str(end) + ") INNER JOIN cost_table ON(edge = lid)")

            # Saving route cost without penalty and updating route_stop.
            cur.execute("SELECT SUM(cost_table.link_cost) AS tot_cost FROM temp_table2 \
            INNER JOIN cost_table ON cost_table.lid = temp_table2.lid;")
            route_stop = cur.fetchone()[0]

            # print("Current cost route " + str(i) + ": " + str(route_stop))

            # if route_stop < route1_cost:
            #     break


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
                            path_seq, agg_cost, speed, fcn_class FROM temp_table2")
                    i = i + 1
                    nr_routes = nr_routes + 1
                    # print("HÄR ÄR VI")
                    overlap_count = 0
                else:
                    # print("OVERLAP STOP")
                    cur.execute(
                        "INSERT INTO result_table SELECT -1 AS did, " + str(start_zone) + " AS start_zone, "
                        + str(end_zone) + " AS end_zone, lid, node, geom, cost, link_cost, start_node, end_node, \
                                            path_seq, agg_cost, speed, fcn_class FROM temp_table2")

                cur.execute("DROP TABLE if exists temp_table1")
                cur.execute("SELECT * INTO temp_table1 from temp_table2")

                overlap_count += 1
                # if stuck in loop for close OD-pairs..
                if overlap_count > 50:
                    break
            else:
                break
        cur.execute("INSERT INTO all_results SELECT * FROM result_table where did > -1")
        conn.commit()
        # No problems
        return 1
    # No route available

    return 3


def fetch_update(limit):
    mac = get_mac()

    #Check if any assignments needs to be finished
    cur_remote.execute("SELECT origin, destination FROM all_od_pairs_test WHERE status = "+str(mac))
    assignment = cur_remote.fetchall()
    #print("assignment: "+str(assignment))

    if not assignment:
        cur_remote.execute("WITH cte AS (select * from all_od_pairs_test "
                    "where (EXTRACT(EPOCH FROM (NOW() - time_updated)) > 1 or time_updated IS NULL) and status = -1 limit "+str(limit)+") "
                    "UPDATE all_od_pairs_test a SET status = "+str(mac)+",assigned_to = "+str(mac)+", time_updated = NOW() FROM cte WHERE  cte.id = a.id;")
        conn_remote.commit()
        cur_remote.execute("SELECT origin, destination FROM all_od_pairs_test WHERE status = "+str(mac))
        assignment = cur_remote.fetchall()

    return assignment

def generate_assignments(my, threshold, max_overlap,assignment):
    print("Starting route set generation")
    status = []
    i = 0
    while i < len(assignment):
        status.append(routeSetGeneration(assignment[i][0], assignment[i][1], my, threshold, max_overlap))
        i += 1

    print("Route set generation complete")
    return status
def insert_results():
    cur.execute("SELECT * FROM all_results")

    all_results = []
    i = 0
    while i < 14:
        if i == 12:
            all_results.append([float(r[i]) for r in cur.fetchall()])
        else:
            all_results.append([r[i] for r in cur.fetchall()])
        cur.execute("SELECT * FROM all_results")
        #print(str((all_results[i])))
        i +=1

    string_conc = "unnest(ARRAY["+str(all_results[0] )+"]"
    i = 1
    while i < 14:
        string_conc += ", (ARRAY["+str(all_results[i] )+"])"
        i += 1
    string_conc += ")"


    print("Starting to insert results!")
    cur_remote.execute("BEGIN TRANSACTION; "
                       "INSERT into remote_results_test select * from "+string_conc +" ON CONFLICT DO NOTHING; "
                                                                                     " COMMIT ;")
    conn_remote.commit()
    print("All results inserted!")

def insert_results_row_wise():
    cur.execute("SELECT * FROM all_results")
    print("Starting to insert results!")

    all_results = []
    i = 0
    while i < 14:
        if i == 12:
            all_results.append([float(r[i]) for r in cur.fetchall()])
        else:
            all_results.append([r[i] for r in cur.fetchall()])
        cur.execute("SELECT * FROM all_results")
        print(str((all_results[i])))
        i += 1

    i = 0
    while i < len(all_results[1]):
        cur.execute("BEGIN TRANSACTION; "
                           "INSERT into remote_results_test (did, start_zone, end_zone,lid,node,geom, cost,link_cost,start_node,"
                    "end_node, path_seq,agg_cost,speed,fcn_class) values (" + str(all_results[0][i]) + ", "+str(all_results[1][i])+" "
                                ", " +str(all_results[2][i])+ ", " +str(all_results[3][i])+  ", " +str(all_results[4][i])+ ", '" +str(all_results[5][i])+
                    "', " +str(all_results[6][i])+ ", " +str(all_results[7][i])+ ", " +str(all_results[8][i])+ ", " +str(all_results[9][i])+
                    ", " +str(all_results[10][i])+ ", " +str(all_results[11][i])+ ", " +str(all_results[12][i])+ ", " +str(all_results[13][i])+ ") "
                                    " ON CONFLICT DO NOTHING;   COMMIT ;")
        i +=1
        conn.commit()

    print("All results inserted!")


def update_result(assignment, status):

    # Update all_od_pairs
    print("Updating results table")
    origin = [r[0] for r in assignment]
    destination = [r[1] for r in assignment]

    cur_remote.execute("create temporary table temp_table as select unnest(ARRAY["+str(origin)+"]) as origin,"
                      " unnest(ARRAY["+str(destination)+"]) as destination, unnest(ARRAY["+str(status)+"]) as status ")

    cur_remote.execute(" BEGIN TRANSACTION;"
                       " UPDATE all_od_pairs_test SET status = temp_table.status, time_updated = NOW() FROM temp_table "
                       " WHERE all_od_pairs_test.origin = temp_table.origin and "
                       " all_od_pairs_test.destination = temp_table.destination; "
                       "COMMIT ;")
    cur_remote.execute("DROP TABLE temp_table")
    conn_remote.commit()
    print("Update complete")

def allowed_update():
    print("Done with script checking if computer can start inserting!")
    while True:
        cur_remote.execute("SELECT mac FROM insert_status WHERE status=(SELECT max(status) FROM insert_status)")
        mymac = cur_remote.fetchone()[0]
        #print("mymac is ", mymac)
        #print("get mac is ", get_mac())
        if (mymac == get_mac()):
            copy_into_special()
            cur_remote.execute("UPDATE insert_status SET status = -1 WHERE mac ="+str(get_mac()))
            conn_remote.commit()
            print("results inserted from mac:"+str(get_mac()))
            break;
        print("checking table")
        time.sleep(2)


def copy_into_table(table, rows):

    cur_remote.execute("CREATE TEMP TABLE IF NOT EXISTS copy_temp_table(did INT, start_zone INT, end_zone INT, lid BIGINT, node BIGINT,"
                       " geom geometry,cost double precision,link_cost DOUBLE PRECISION, start_node BIGINT, end_node BIGINT,path_seq INT,agg_cost DOUBLE PRECISION,"
                       "speed numeric, fcn_class BIGINT, PRIMARY KEY (start_zone, end_zone,did, path_seq))")

    sio = StringIO()
    print("1 fast")
    sio.write('\n'.join('%s %s %s %s %s %s %s %s %s %s %s %s %s %s' % x for x in rows))
    sio.seek(0)
    print("2 fast")
    cur_remote.copy_from(sio, "copy_temp_table", sep =' ')
    conn_remote.commit()
    print("3 fast")
    cur_remote.execute("BEGIN TRANSACTION; "
                       "INSERT into "+table+" select * from copy_temp_table ON CONFLICT DO NOTHING; COMMIT ;")
    conn_remote.commit()


def copy_into_special():
    cur.execute("SELECT * FROM all_results")

    rows = []
    i = 0
    for x in cur.fetchall():

        rows.append(x)

    copy_into_table( "remote_results_test", rows)


# End of function definitions

# Connection global to be used everywhere.
#TP4030
conn = psycopg2.connect(host="localhost", database="mattugusna", user="postgres")

#Gustav och Mattias
#conn = psycopg2.connect(host="localhost", database="exjobb", user="postgres", password="password123",port=5432)

conn.autocommit = True
cur = conn.cursor()

#TP4030
conn_remote = psycopg2.connect(host="192.168.1.10", database="mattugusna", user="mattugusna", password="password123")

#Gustav och Mattias
#conn_remote = psycopg2.connect(host="localhost", database="mattugusna", user="mattugusna", password="password123",port=5455)

conn_remote.autocommit = False
cur_remote = conn_remote.cursor()

def main():
    tic()
    print("Mac: ",get_mac())
    # Variable definitions
    my = 0.01
    threshold = 1.3
    max_overlap  = 0.8
    limit = 100

    cur.execute("DROP TABLE if exists all_results")

    i = 0
    while i < 1:
        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
        print("Start: " + dt_string)
        try:
            assignment=fetch_update(limit)

            if not assignment:
                break

            status = generate_assignments(my, threshold, max_overlap,assignment)
            update_result(assignment, status)
            now = datetime.now()
            dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
            print("Klar med "+str(limit)+"st kl: " + dt_string)

        except Exception as exptest:
            conn_remote.commit()
            print("Exception i While loop "+ str(exptest))

    allowed_update()


if __name__ == "__main__" or __name__ == "__console__":
    main()

#Close connection and cursor
conn.commit()
cur.close()
conn.close()
toc();
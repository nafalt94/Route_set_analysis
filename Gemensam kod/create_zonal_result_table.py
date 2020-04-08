# Imports
import time
import sys
from datetime import datetime
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
        # print("Elapsed time: %f seconds.\n" % tempTimeInterval)
        return tempTimeInterval
def tic():
    # Records a time in TicToc, marks the beginning of a time interval
    toc(False)


# Initialize TicToc function.
TicToc = TicTocGenerator()

def createEmmeResults(origins,destinations, removed_lids):

    # Här vill jag skapa nytt lager som visar intressanta saker för varje zon
    # Create emme_result table
    # cur_remote.execute("DROP table if exists emme_results")
    # cur_remote.execute("SELECT 0 as nr_non_affected, 0 as nr_no_routes, 0 as nr_all_routes_affected, 0.0 "
    #                    "as mean_deterioration, 0 as nr_pairs,* INTO emme_results FROM emme_zones")

    removed_lid_string = "( lid = " + str(removed_lids[0])
    i = 1
    while i < len(removed_lids):
        removed_lid_string += " or lid =" + str(removed_lids[i])
        i += 1
    removed_lid_string += ")"

    i = 0
    sum = 0
    count = 0

    while i < len(origins):
        # Returns [#non affected zones, #no routes in OD-pair, #all routes affected, mean_deterioration, #pairs]
        #[count3,count2,count1, mean_detour, i-1]

        effect = odEffect(origins[i], destinations[i], removed_lid_string)
        if effect != -1:
            sum += effect
            count += 1

        #if last iteration, terminate and if last pair of current start_zone, update and go to next
        if (i == len(origins) - 1) or (origins[i] != origins[i + 1]):

            #If no alternative route exists
            if sum == 0:
                mean_det = -1
            else:
                mean_det = sum/count
            # result is: [?,?,?,mean_deterioration,?]
            result = [1, 0, 0, mean_det, 0]
            cur_remote.execute("UPDATE emme_results SET nr_non_affected = " + str(result[0]) + " , nr_no_routes = " +
                str(result[1]) + " , nr_all_routes_affected = " +
                str(result[2]) + " , mean_deterioration = " +
                str(result[3]) + " , nr_pairs = " + str(result[4]) + " WHERE id = " +
                str(origins[i]) + ";")
            sum = 0
            count = 0
        i += 1

def analysis_multiple_zones(start_node, list, lids):
    count3 = 0
    count2 = 0
    count1 = 0
    count_detour = 0
    sum_detour = 0

    removed_lid_string = "( lid = " + str(lids[0])
    i = 1
    while i < len(lids):
        removed_lid_string += " or lid =" + str(lids[i])
        i += 1
    removed_lid_string += ")"

    i = 0
    while i < len(list):
        if start_node != list[i]:
            result_test = odEffect(start_node, list[i], removed_lid_string)

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

        if count_detour != 0:
            mean_detour = sum_detour/count_detour
        else:
            mean_detour = -1
    return [count3,count2,count1, mean_detour, i-1]

def odEffect(start, end, removed_lid_string):
    start_zone = start
    end_zone = end

    # Finding best, non-affected alternative route
    cur_remote.execute("SELECT MIN(did) FROM remote_results WHERE "
                      " start_zone = "+str(start_zone)+" AND end_zone = "+str(end_zone)+" AND "
                    " did NOT IN (select did from remote_results where start_zone = "+str(start_zone)+" AND end_zone = "+str(end_zone)+" AND  "+ removed_lid_string+ ")")

    id_alt = str(cur_remote.fetchone()[0])
    print("id_alt är: "+ id_alt)
    print("start är " + str(start))

    if id_alt == "None":
        print("gick in för none")
        return -1
    else:
        # print("Zon påverkas och bästa id är:" + id_alt)

        # Fetching cost of the optimal route and the alternative
        cur_remote.execute("SELECT sum(link_cost) from remote_results where "
                          " (start_zone = " + str(start_zone) + " AND end_zone = " + str(end_zone) + ") AND "
                            "(did = 1 OR did = " + str(id_alt) + ") group by did")
        # Best cost
        cost_opt = str(cur_remote.fetchone()[0])

        # Alternative cost
        cost_alt = str(cur_remote.fetchone()[0])

        # Proportion of extra cost of alternative route in relation to opt route
        # print("cost_opt = " + cost_opt + " and cost_alt = " + cost_alt)
        return (float(cost_alt) / float(cost_opt))

def affected_pairs(lids):

    #Create string of chosen lids to analyse
    removed_lid_string = "( lid = " + str(lids[0])
    i = 1
    while i < len(lids):
        removed_lid_string += " or lid =" + str(lids[i])
        i += 1
    removed_lid_string += ")"

    # ORDER BY verkar ta tid. Att göra: indexera remote_results på start_zone
    cur_remote.execute("select start_zone,end_zone from remote_results where did = 1 and " + removed_lid_string+" order by start_zone limit 20")

    all_pairs = cur_remote.fetchall()
    origins = [r[0] for r in all_pairs]
    destinations = [r[1] for r in all_pairs]

    return [origins, destinations]


# Connection global to be used everywhere.
conn_remote = psycopg2.connect(host="localhost", database="mattugusna", user="mattugusna", password="password123",port=5455)
conn_remote.autocommit = True
cur_remote = conn_remote.cursor()


def main():
    tic()
    removed_lids = [83025,84145,83443]

    # cur_remote.execute("select start_zone from remote_results group by start_zone limit 10")
    # all_zones = cur_remote.fetchall()
    # list = [r[0] for r in all_zones]
    # list.append(7789)
    # list.append(7251)
    # print(str(list))

    # print(str(odEffect(7789, 7251, [83443, 84145])))
    # print(str(odEffect(6772, 6773, [83443, 84145])))

    lists = affected_pairs(removed_lids)
    print("klart med lista")
    createEmmeResults(lists[0],lists[1], removed_lids)

    #print(str(affected_pairs(removed_lids)[0]))
    toc()



if __name__ == "__main__" or __name__ == "__console__":
    main()

#Close connection and cursor
conn_remote.commit()
cur_remote.close()
conn_remote.close()
toc();
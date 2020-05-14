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

def createEmmeResults(origins,destinations, removed_lids,tabel_nr):

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
    sum_all_affected = 0
    count = 0

    print_count = 1

    while i < len(origins):

        if i == round(print_count * len(origins) / 100):
            print_count += 1
            now = datetime.now()
            dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
            print("Finished with " + str(100*i / len(origins)) + "% kl: " + dt_string)

        effect = odEffect(origins[i], destinations[i], removed_lid_string,tabel_nr)
        if effect != -1:
            sum += effect
            count += 1
        else:
            sum_all_affected += 1

        #if last iteration, terminate and if last pair of current start_zone, update and go to next
        if (i == len(origins) - 1) or (origins[i] != origins[i + 1]):

            #If no alternative route exists
            if sum == 0:
                mean_det = -1
            else:
                mean_det = sum/count

            #För att inkludera nollor..
            #1125 is the number of distinct end_zones
            mean_det_all = sum / 1125

            # result is: [nr all routes affected,mean_deterioration,nr affected OD-pairs]
            result = [sum_all_affected,mean_det,mean_det_all,(count + sum_all_affected)]
            cur_remote.execute("UPDATE emme_results SET nr_all_routes_affected = " + str(result[0]) + " , mean_deterioration = " +
                str(result[1]) + ", mean_deterioration_all = " +str(result[2]) + ", nr_affected = " + str(result[3]) + "  WHERE id = " + str(origins[i]) + ";")
            sum = 0
            sum_all_affected = 0
            count = 0
        i += 1

def odEffect(start, end, removed_lid_string,tabel_nr):
    start_zone = start
    end_zone = end

    # Finding best, non-affected alternative route
    cur_remote.execute("SELECT MIN(did) FROM remote_results"+str(tabel_nr)+" WHERE "
                      " start_zone = "+str(start_zone)+" AND end_zone = "+str(end_zone)+" AND "
                    " did NOT IN (select did from remote_results"+str(tabel_nr)+" where start_zone = "+str(start_zone)+" AND end_zone = "+str(end_zone)+" AND  "+ removed_lid_string+ ")")

    id_alt = str(cur_remote.fetchone()[0])
    #print("id_alt är: "+ id_alt)
    #print("start är " + str(start))

    if id_alt == "None":
        #print("gick in för none")
        return -1
    else:
        # print("Zon påverkas och bästa id är:" + id_alt)

        # Fetching cost of the optimal route and the alternative
        cur_remote.execute("SELECT sum(link_cost) from remote_results"+str(tabel_nr)+" where "
                          " (start_zone = " + str(start_zone) + " AND end_zone = " + str(end_zone) + ") AND "
                            "(did = 1 OR did = " + str(id_alt) + ") group by did")
        # Best cost
        cost_opt = str(cur_remote.fetchone()[0])

        # Alternative cost
        cost_alt = str(cur_remote.fetchone()[0])

        # Proportion of extra cost of alternative route in relation to opt route
        # print("cost_opt = " + cost_opt + " and cost_alt = " + cost_alt)
        return (float(cost_alt) / float(cost_opt))

def affected_pairs(lids,tabel_nr):

    #Create string of chosen lids to analyse
    removed_lid_string = "( lid = " + str(lids[0])
    i = 1
    while i < len(lids):
        removed_lid_string += " or lid =" + str(lids[i])
        i += 1
    removed_lid_string += ")"

    # ORDER BY verkar ta tid. Att göra: indexera remote_results på start_zone
    cur_remote.execute("select distinct start_zone,end_zone from remote_results"+str(tabel_nr)+" where " + removed_lid_string+" and did = 1 order by start_zone ")

    all_pairs = cur_remote.fetchall()
    origins = [r[0] for r in all_pairs]
    destinations = [r[1] for r in all_pairs]

    return [origins, destinations]


# Connection global to be used everywhere.
#TP4030
conn_remote = psycopg2.connect(host="192.168.1.10", database="mattugusna", user="mattugusna", password="password123")
#Gustav och Mattias
#conn_remote = psycopg2.connect(host="localhost", database="mattugusna", user="mattugusna", password="password123", port=5455)
conn_remote.autocommit = True
cur_remote = conn_remote.cursor()


def main():
    tic()

    # Gamla lids
    # removed_lids = [83025, 84145, 83443, 82268, 82267]
    # Gröndalsbron
    #removed_lids = [82763, 83481]

    #Gröndalsbron endast södergående
    # removed_lids = [83481]

    #Tranebergsbron
    #removed_lids = [82697,82717]

    #Götgatan
    #removed_lids = [91116, 87551, 92885, 93752, 94922, 81082, 91081, 89227, 89228, 88721, 88720, 89385, 89384, 89387]

    #Götgatan mitt på vägen
    removed_lids = [89227, 89228]

    #Alla överfarter till södermalm
    # removed_lids = [82587, 83042,87369,89102,91089,94139,94140,
    #                 95360,95361,80922,83802,82323,82386,87551,89520,
    #                 89519,91116,90016,90112,86516,93046,]

    # cur_remote.execute("select start_zone from remote_results group by start_zone limit 10")
    # all_zones = cur_remote.fetchall()
    # list = [r[0] for r in all_zones]
    # list.append(7789)
    # list.append(7251)
    # print(str(list))

    # print(str(odEffect(7789, 7251, [83443, 84145])))
    # print(str(odEffect(6772, 6773, [83443, 84145])))


    #För att ta reda på vilken tabell som ska arbetas med:
    cur_remote.execute("SELECT update_order FROM insert_status WHERE mac = " + str(get_mac()))
    tabel_nr = cur_remote.fetchone()[0]

    lists = affected_pairs(removed_lids,tabel_nr)
    print("klart med lista")
    createEmmeResults(lists[0],lists[1], removed_lids,tabel_nr)
    print("Klar")

    #print(str(affected_pairs(removed_lids)[0]))
    toc()



if __name__ == "__main__" or __name__ == "__console__":
    main()

#Close connection and cursor
conn_remote.commit()
cur_remote.close()
conn_remote.close()
toc();
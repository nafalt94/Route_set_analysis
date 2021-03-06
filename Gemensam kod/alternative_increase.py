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

def affected_pairs(lids,tabel_nr):

    #Create string of chosen lids to analyse
    removed_lid_string = "( lid = " + str(lids[0])
    i = 1
    while i < len(lids):
        removed_lid_string += " or lid =" + str(lids[i])
        i += 1
    removed_lid_string += ")"

    # ORDER BY verkar ta tid. Att göra: indexera remote_results på start_zone
    cur_remote.execute("select distinct start_zone,end_zone from remote_results" + str(tabel_nr) + " where "
                       + removed_lid_string + " and did = 1 order by start_zone")

    all_pairs = cur_remote.fetchall()
    origins = [r[0] for r in all_pairs]
    destinations = [r[1] for r in all_pairs]

    return [origins, destinations]




def add_to_table(list, lids, tabel_nr):

    cur_remote.execute("CREATE TABLE if not exists increasing_alternative" + str(tabel_nr) + "(lid BIGINT)")
    # Create string of chosen lids to analyse
    removed_lid_string = "( lid = " + str(lids[0])
    i = 1
    while i < len(lids):
        removed_lid_string += " or lid =" + str(lids[i])
        i += 1
    removed_lid_string += ")"

    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    print("Insert börjar " + dt_string)
    i=0
    print_count = 1
    while i < np.size(list, 1):
        # cur_remote.execute("INSERT INTO increasing_alternative select lid, count(lid) from remote_results_no_ferries" + str(tabel_nr) + " WHERE start_zone = "+str(list[0][i])+" AND end_zone = "+str(list[1][i])+" AND "
        #             " did NOT IN (select did from remote_results_no_ferries" + str(tabel_nr) + " where start_zone = "+str(list[0][i])+" AND end_zone = "+str(list[1][i])+" AND " + removed_lid_string+") group by lid "
        #             " ON CONFLICT (lid) DO UPDATE "
        #             " SET count = increasing_alternative.count+excluded.count; ")
        if i == round(print_count * np.size(list, 1) / 10):
            print_count += 1
            now = datetime.now()
            dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
            print("Finished with " + str(round(i / np.size(list, 1), 2)) + " time: " + dt_string)

        # För alla alternativa rutter
        # cur_remote.execute(
        #     "INSERT INTO increasing_alternative" + str(tabel_nr) + " select lid from remote_results" + str(
        #         tabel_nr) + " WHERE start_zone = " + str(list[0][i]) + " AND end_zone = " + str(list[1][i]) + " AND "
        #         " did NOT IN (select did from remote_results" + str(
        #         tabel_nr) + " where start_zone = " + str(list[0][i]) + " AND end_zone = " + str(
        #         list[1][i]) + " AND " + removed_lid_string + ")")

        # För näst bästa alternativet som inte använder removed lids.
        cur_remote.execute(
                "INSERT INTO increasing_alternative" + str(tabel_nr) + " select lid from remote_results" + str(
                    tabel_nr) + " WHERE start_zone = " + str(list[0][i]) + " AND end_zone = " + str(list[1][i]) + " AND "
                    " did NOT IN (select did from remote_results" + str(
                    tabel_nr) + " where start_zone = " + str(list[0][i]) + " AND end_zone = " + str(
                    list[1][i]) + " AND " + removed_lid_string + ")")

        i += 1

    print("Klar med add to table i är:"+ str(i))


def affected_pairs_start_zone(lids):

    #Create string of chosen lids to analyse
    removed_lid_string = "( lid = " + str(lids[0])
    i = 1
    while i < len(lids):
        removed_lid_string += " or lid =" + str(lids[i])
        i += 1
    removed_lid_string += ")"

    # ORDER BY verkar ta tid. Att göra: indexera remote_results på start_zone
    cur_remote.execute("select distinct start_zone from partitioned_results where "
                       + removed_lid_string + " and did = 1 order by start_zone")

    all_pairs = cur_remote.fetchall()
    origins = [r[0] for r in all_pairs]

    return [origins]



def add_to_table_start_zone(list, lids):


    #cur_remote.execute("CREATE TABLE if not exists increasing_alternative(lid BIGINT, count BIGINT, PRIMARY KEY(lid))")

    # Test med count
    cur_remote.execute("CREATE TABLE if not exists increasing_alternative(start_zone BIGINT)")
    # Create string of chosen lids to analyse
    removed_lid_string = "( lid = " + str(lids[0])
    i = 1
    while i < len(lids):
        removed_lid_string += " or lid =" + str(lids[i])
        i += 1
    removed_lid_string += ")"

    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    print("Insert börjar " + dt_string)
    i=0
    print_count = 1
    while i < np.size(list, 1):
        if i == round(print_count * np.size(list, 1) / 10):
            print_count += 1
            now = datetime.now()
            dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
            print("Finished with " + str(round(i / np.size(list, 1), 2)) + " time: " + dt_string)

        # För alla alternativa rutter
        # cur_remote.execute(
        #     "INSERT INTO increasing_alternative" + str(tabel_nr) + " select lid from remote_results" + str(
        #         tabel_nr) + " WHERE start_zone = " + str(list[0][i]) + " AND end_zone = " + str(list[1][i]) + " AND "
        #         " did NOT IN (select did from remote_results" + str(
        #         tabel_nr) + " where start_zone = " + str(list[0][i]) + " AND end_zone = " + str(
        #         list[1][i]) + " AND " + removed_lid_string + ")")

        # För näst bästa alternativet som inte använder removed lids.
        cur_remote.execute("INSERT INTO increasing_alternative select lid, count(*) from "
        "(SELECT p.did, p.start_zone, p.end_zone, p.lid, p.link_cost, p.path_seq "
        "FROM partitioned_results p WHERE start_zone = " + str(list[0][i]) + " "
        "and (did, end_zone) in (select distinct max(did) + 1, end_zone "
        "from partitioned_results where " + removed_lid_string + " and start_zone = " + str(list[0][i]) + " group by "
        "end_zone)) b group by lid ON CONFLICT(lid) DO UPDATE SET count = excluded.count + increasing_alternative.count")

        # TEST MED räkna start zoner
        # cur_remote.execute("INSERT INTO increasing_alternative select end_zone from "
        #                    "(SELECT distinct p.start_zone, p.end_zone, p.did "
        #                    "FROM partitioned_results p WHERE start_zone = " + str(list[0][i]) + " "
        #                     "and (did, end_zone) in (select distinct max(did) + 1 , end_zone "
        #                     "from partitioned_results where  "+removed_lid_string+" and start_zone = " + str(list[0][i]) + " "
		# 											"group by end_zone)) b")


        i += 1

    print("Klar med add to table i är:"+ str(i))


# Connection global to be used everywhere.

#TP4030
#conn = psycopg2.connect(host="localhost", database="mattugusna", user="postgres")

#Gustav och Mattias
# conn = psycopg2.connect(host="localhost", database="exjobb", user="postgres", password="password123",port=5432)
#
# conn.autocommit = True
# cur = conn.cursor()

# Connection global to be used everywhere.
#TP4030
#conn_remote = psycopg2.connect(host="192.168.1.10", database="mattugusna", user="mattugusna", password="password123")

#Gustav och Mattias
conn_remote = psycopg2.connect(host="localhost", database="mattugusna", user="mattugusna", password="password123", port=5455)

conn_remote.autocommit = True
cur_remote = conn_remote.cursor()

def main():
    tic()
    # Gröndalsbron
    removed_lids = [82763, 83481]

    #Alla överfarter till södermalm
    # removed_lids = [82587, 83042,87369,89102,91089,94139,94140,
    #                 95360,95361,80922,83802,82323,82386,87551,89520,
    #                 89519,91116,90016,90112,86516,93046,]

    # Tranebergsbron
    #removed_lids = [82697, 82717]

    #Götgatan
    #removed_lids = [89227, 89228]


    #Gröndalsbron söder
    #removed_lids = [83481]

    print("Mac: ", get_mac())
    #För att ta reda på vilken tabell som ska arbetas med:
    # cur_remote.execute("SELECT update_order FROM insert_status WHERE mac = " + str(get_mac()))
    # tabel_nr = cur_remote.fetchone()[0]
    tabel_nr = 1
    cur_remote.execute("DROP TABLE if exists increasing_alternative")

    lists = affected_pairs(removed_lids,tabel_nr)


    print("Number of start zones effected " + str(np.size(lists,1)))

    add_to_table(lists, removed_lids,tabel_nr)

    #print(str(affected_pairs(removed_lids)[0]))
    toc()



if __name__ == "__main__" or __name__ == "__console__":
    main()

#Close connection and cursor
conn_remote.commit()
cur_remote.close()
conn_remote.close()
toc();
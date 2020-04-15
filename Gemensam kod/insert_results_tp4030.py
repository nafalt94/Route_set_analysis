
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
        # print(str((all_results[i])))
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
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    print("Start: " + dt_string)

    insert_results()



    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    print("end: " + dt_string)

if __name__ == "__main__" or __name__ == "__console__":
    main()

#Close connection and cursor
conn.commit()
cur.close()
cur_remote.close()
conn.close()
conn_remote.close()

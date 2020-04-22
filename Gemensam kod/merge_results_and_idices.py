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
def funtion():
    print("test")
    cur_remote.execute("drop table if exists remote_results_merged")
    cur_remote.execute("CREATE TABLE IF NOT EXISTS remote_results_merged(did INT, start_zone INT, end_zone INT, lid BIGINT, node BIGINT, "
                     "geom geometry,cost double precision,link_cost DOUBLE PRECISION, start_node BIGINT, end_node BIGINT,path_seq INT,agg_cost DOUBLE PRECISION, "
                     " speed numeric, fcn_class BIGINT, PRIMARY KEY (start_zone, end_zone,did, path_seq))")
    conn_remote.commit()
    cur_remote.execute("INSERT INTO remote_results_merged SELECT * FROM remote_results_5025763207074;")
    conn_remote.commit()
    cur_remote.execute("INSERT INTO remote_results_merged SELECT * FROM remote_results_189794999289111;")
    conn_remote.commit()




#TP4030
#conn_remote = psycopg2.connect(host="192.168.1.10", database="mattugusna", user="mattugusna", password="password123")

#Gustav och Mattias
conn_remote = psycopg2.connect(host="localhost", database="mattugusna", user="mattugusna", password="password123",port=5455)

conn_remote.autocommit = False
cur_remote = conn_remote.cursor()

def main():
    print("Mac: ",get_mac())
    funtion()





if __name__ == "__main__" or __name__ == "__console__":
    main()
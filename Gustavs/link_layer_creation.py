
db.exec_("DROP table if exists OD_lines_all")
    db.exec_("SELECT ST_MakeLine(ST_Centroid(geom) ORDER BY id) AS geom into OD_lines_all FROM emme_zones"
             " where id = "+str(start_list[0])+" OR id = "+ str(end_list[0]) +" ")
    i = 1
    while i < len(start_list):
        db.exec_("INSERT INTO OD_lines_all(geom) SELECT ST_MakeLine(ST_Centroid(geom) ORDER BY id) "
                 "AS geom FROM emme_zones where id = "+str(start_list[i])+" OR id = "+str(end_list[i])+"")
        i = i + 1
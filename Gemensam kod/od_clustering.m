tic
% Add jar file to classpath (ensure it is present in your current dir)
javaclasspath('postgresql-8.3-603.jdbc3.jar');

query = ['select id_ori,id_dest, ST_x(geom_ori) as x_origin, ST_y(geom_ori) as y_origin, ' ...
'ST_x(geom_dest) as x_dest, ST_y(geom_dest) as y_dest,ST_length(geom_line) as dis from all_od_pairs'] ;

databasename = 'exjobb';
username = 'gustav';
password = 'password123';
driver = 'org.postgresql.Driver';
url = 'jdbc:postgresql://localhost:5432/exjobb';

conn = database(databasename,username,password,driver,url);
data = select(conn,query);

data = table2array(data);
data = double(data);
idx = kmedoids((data),50);

close(conn)
toc
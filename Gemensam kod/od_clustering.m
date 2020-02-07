% Add jar file to classpath (ensure it is present in your current dir)
javaclasspath('postgresql-8.3-603.jdbc3.jar');

% Username and password you chose when installing postgres
props=java.util.Properties;
props.setProperty('user', 'tnk106');
props.setProperty('password', 'positioning_systems');

% Create the database connection (port 5432 is the default)
driver=org.postgresql.Driver;
url = 'jdbc:postgresql://localhost:5432/senzoor';
conn=driver.connect(url, props);

sql_fp = ['SELECT *, extract(EPOCH from time) as time2 FROM tnk106.bt_search_group_2 where '] ;
    sql_fp = strcat(sql_fp,'',' extract(EPOCH from time) > ' ,'', num2str((curTime - t)), ' ');

    
    pause(1)
    ps=conn.prepareStatement(sql_fp);
    rs=ps.executeQuery();
    
    clear row_id ;
    clear time;
    clear  mac ;
    clear  rss ;
    clear x_est ;
    clear y_est ;
    
    count=1;
    while rs.next()
        row_id(count) = rs.getInt('row_id');
        time(count) = str2double(rs.getString('time2'));
        mac(count) = rs.getString('mac');
        rss(count) = rs.getInt('rss');
        count=count+1;
    end
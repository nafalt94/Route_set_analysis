tic
% Add jar file to classpath (ensure it is present in your current dir)
javaclasspath('postgresql-8.3-603.jdbc3.jar');

query = ['select did, path_seq,fcn_class, speed from all_results ' ...
    ' order by did, path_seq'] ;

databasename = 'exjobb';
username = 'gustav';
password = 'password123';
driver = 'org.postgresql.Driver';
url = 'jdbc:postgresql://localhost:5432/exjobb';

conn = database(databasename,username,password,driver,url);
data = select(conn,query);

data = table2array(data);

indexes = 1:data(length(data)) +1 ;
 
count = 1;
for i=1:length(data)
    if data(i,1) ~= indexes(count)
       indexes(count) = i-1;
       count = count + 1;
       
       if data(i,1) == 2
           plot(1:i,7 - data(1:i,3),'color','b')
           hold on
       else
           plot((indexes(count-2):1:indexes(count-1)),7 - data(indexes(count-2):indexes(count-1),3),'color',rand(1,3))
       end
    end
end
indexes(count) = length(data);
plot((indexes(count-1):1:indexes(count)),7 - data(indexes(count-1):indexes(count),3),'color',rand(1,3))


%plot(7 - data(1:59,3))

close(conn)
toc
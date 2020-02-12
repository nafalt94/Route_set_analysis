rm(list = ls()) #Removes all

require("RPostgreSQL")

library(cluster)
library(factoextra)

# create a connection
# save the password that we can "hide" it as best as we can by collapsing it
pw <- {
  "password123"
}

# loads the PostgreSQL driver
drv <- dbDriver("PostgreSQL")
# creates a connection to the postgres database
# note that "con" will be used later in each connection to the database
con <- dbConnect(drv, dbname = "exjobb",
                 host = "localhost", port = 5432,
                 user = "gustav", password = pw)
rm(pw) # removes the password

# check for the emme_zones
dbExistsTable(con, "all_od_pairs")
dbExistsTable(con, "model_graph")
# TRUE

# query the data from postgreSQL 
od_matrix <- dbGetQuery(con, "select id_ori,id_dest, ST_x(geom_ori) as x_origin, ST_y(geom_ori) as y_origin,
ST_x(geom_dest) as x_dest, ST_y(geom_dest) as y_dest, 
ST_length(geom_line) as dis,geom_line as geom from all_od_pairs" )
 

od_matrix.new<- od_matrix[,c(3,4,5,6,7)]

normalize <- function(x){
  return ((x-min(x))/(max(x)-min(x)))
}

od_matrix.new$x_origin <- normalize(od_matrix.new$x_origin)
od_matrix.new$y_origin <- normalize(od_matrix.new$y_origin)
od_matrix.new$x_dest <- normalize(od_matrix.new$x_dest)
od_matrix.new$y_dest<- normalize(od_matrix.new$y_dest)
od_matrix.new$dis<- normalize(od_matrix.new$dis)

head(od_matrix.new)

result<- kmeans(od_matrix.new,50) #aplly k-means algorithm with no. of centroids(k)=3
result$size # gives no. of records in each cluster
#result$cluster
result_cluster = result$cluster
#result$medoids

#od_matrix including cluster
od_matrix_result = cbind(od_matrix, result$cluster)

#par(mfrow=c(2,2), mar=c(5,4,2,2))
#plot(od_matrix.new[c(1,2)], col=result$cluster)# Plot to see how Sepal.Length and Sepal.Width data points have been distributed in clusters
#plot(od_matrix.new[c(1,2)], col=od_matrix.class)# Plot to see how Sepal.Length and Sepal.Width data points have been distributed originally as per "class" attribute in dataset
#plot(od_matrix.new[c(3,4)], col=result$cluster)# Plot to see how Petal.Length and Petal.Width data points have been distributed in clusters
#plot(od_matrix.new[c(3,4)], col=od_matrix.class)



## Writing to DB
dbWriteTable(con, "cluster_result", od_matrix_result, append = F) 

# sen skriv detta i postgresql: ALTER TABLE cluster_result ALTER COLUMN geom TYPE Geometry USING geom::Geometry;

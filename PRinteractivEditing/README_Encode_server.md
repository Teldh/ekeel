# PREREQUISITE CONCEPT MAPS based on Topic Maps
# Encode Server
Encode is the server side of the application Encode on Web

# Installation

1- Download the repository content.

2- Create the db schema using script encode_v2_server-master/documentation/ENCODE_Database.sql MySql script. (SQL version also in the folder)

3- Install Apache Maven if you don't already have it, https://maven.apache.org/download.cgi.

4- Open a shell and go in /encode_v2_server-master.

5- Create a Jar of backend layer running the "mvn package" command.


# Access to the Swagger Documentation

1- Run the server (Run the command " java -jar encode-rest-api-0.0.1-develop.jar")

2- The default address is http://localhost:8080/swagger-ui.html#/ 

3- To access a component add the name of the controller : ex: http://localhost:8080/swagger-ui.html#/association-controller

4- To access directly a method, you add "$name of the method in the controller class"Using"$HTTP METHOD": ex: http://localhost:8080/swagger-ui.html#/association-controller/createAssociationUsingPOST

# Test REST API

The API Request are in .idea>httpRequests>controllerRequests
0. From client side create a user
1. Post User login & get token
2. Post schema
3. Post topicMap which uses the previously defined schema
4. Post TopicType
5.1 Post AssociationType with Roles
5.2 Patch http://localhost:8080/protected/v1/associationType/1/role/2/topicTypes [2,3] With the ids given here, we will give to the TopicType with id 2 and 3 the Role with id 2 of the Association Type with id 1.
Then another Patch call can be done to set to TopicType 2 the role 1 http://localhost:8080/protected/v1/associationType/1/role/1/topicTypes [2] in this way topic type 2 could have both role 1 and 2
6. Post OccurrenceType
7. Post scope
8. Post effortType
9. Post Topic
10. Post Association 

Be careful, use the methods in .idea>httpRequests>controllerRequests for testing, if you try to use the methods directly via swagger they will not work

If you encounter problems with the DB link, be sure to check the application.properties file in encode_v2_server-master/src/main/resource

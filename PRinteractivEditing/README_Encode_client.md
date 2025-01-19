# PREREQUISITE CONCEPT MAPS based on Topic Maps
# EncodeWeb
Encode on Web is an Application that give to user the opportunity to project and manage Educational Concept Maps via browser.

# Installation

1- Download the repository content.

2- Create the db schema using script encode_v2_server-master/documentation/ENCODE_Database.sql MySql script.

3- Install Apache Maven if you don't already have it, https://maven.apache.org/download.cgi.

4- Open a shell and go in /encode_rest_api folder.

5- Create a Jar of backend layer running the "mvn package" command.

6- Install Node.js from https://nodejs.org/it/

7- Open a shell and go to /unige_encode_v2_client-master folder.

8- Run the command "npm install" with the aim of install all projet dependency.

# Execution

1- Open a shell and go to encode encode-rest-api-0.0.1-develop.jar location (it should be in /unige_encode_v2_client-master/target folder )

2- Run the command " java -jar encode-rest-api-0.0.1-develop.jar"

3- Open a shell and go to  /unige_encode_v2_client-master folder.

4- Run the command "npm start"

# Usage

1- Open chrome browser and go to URL "http://localhost:3000"

2- Enjoy :) !

# Interface functionalities to be added soon

1- Possibility of generating an html page containing materials relating to a given topic map

2- Possibility of generating and modifying a lesson plan

3- Possibility to download and upload concept maps

4- A full management of editors

5- A full management for association type roles (in the current version there is only the assignment of an association type role to a certain topic type)

6- Graph representation compliance & N-arry relations

7- A new page for Association management, as they can now be more than binary

8- Effort management on occurrences

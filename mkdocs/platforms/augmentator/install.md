# Video augmentation and graph exploration
------


## Short description of the project:

This project is a web application developped in React (JS) for the front-end and with Flask for the back-end (Python). The aim of the application is to help students learn through videos, contextual help and an interactive knowledge graph gathering all the concepts explainend in the video and the relationships with each other.

[Here](https://drive.google.com/drive/folders/1o9WdAvNopdtUSw5h2tq0q5QBMCZbrNIk?usp=sharing) is a Drive folder of demo of the features

<br>

--------
## Installation

### Virtual Environment

To organize the projecty it is better to create and use a virtual env as Annotator app, but you can skip this step.

### Prerequisites: Anaconda  


Ensure Anaconda/Conda configured in terminal:

To install Conda follow [this guide](../../prerequisites/conda.md) 

------
### Back-end (Flask)

* Make sure that you have Flask installed on your machine

* Go inside flask-server folder:
```
cd src/flask-server
conda env create -f conda_environment.yml
conda activate ekeel_aug_env
```

#### On any Change in Environment Packages 

To avoid inconsistency between local and server, yml file has been used to enforce same environment state

open a terminal:
  > cd {inside folder EKEELVideoAugmentation/src/flask-server}


overwrite the conda_environment.yml inside using
```
conda env export --no-builds | grep -v "^prefix: " | grep -v "en-core-web-lg" | grep -v "it-core-news-lg" > conda_environment.yml
```
and push the modifications to the repo. (The spacy models end up in the final distribution but must be ignored otherwise cause errors)

Then to synchronize the packages change in the server pull updates from the repo and on the server terminal update dependencies on the server:

The guide is [here](deploy.md#update-and-setup-video-augmentation-app)


* If you need to connect to EKEEL’s mail box:
  - Go to Gmail’s login interface
  - Email address : Specified in the `.env` file as `EMAIL_ACCOUNT`
  - Password : Specified in the `.env` file as `EMAIL_PASSWORD`

------
### Front-end (React.js)

* Make sure that Node.js v16.20.2 (and npm v8.19.4) are installed on the machine

Suggest install nvm to manage different environments
```
nvm install 16
nvm use 16
```

* Go inside react-app folder
```
cd src/react-app  
```

* Install the dependencies
```
npm install --legacy-peer-deps
```

-----
## Notes

- Pymongo issues 

  if pymongo certificate is invalid:
    1. Download https://letsencrypt.org/certs/lets-encrypt-r3.pem 
    2. rename file .pem to .cer
    3. double click and install   
  
<br>

- To make graphs the same in 1st and this app we commented the call to the function for removing transitivity.

  * to reactivate transitivity go to line 452 of GraphKnowledge.js and decomment the line with the call.

  * // this.removeTransitivity(this.state.graph)

<br>

- Change annotation to display/consider:

  To change annotations have a look on this part of the code:

  * data.py (get_concept_instants, get_concept_vocabulary, get_concept_map, get_concept_list)

  * handle_data.py (get_definitions_fragments)

  * main.py (get_fragments, class Graphs, get_graph, graph)

  Atm on each of thoose functions the email or annotatorId fields/var are used as a filter to the DB.
  Change user informations to update the filter and obtain other annotations as result.
  This can be done also with burst or gold annotations.

<br>

- Videos folder

  the videos folder inside main.py (line ~28) has to be arranged basing on the server folder structure.

  ```python
    app.config["CLIENT_IMAGES"] = 
    "/var/www/edurell/EVA_apps/EKEELVideoAnnotation/static/videos"
  ```
<br>

- Email 

    After some months the email sender could stop working and you can find errors on register or forgot password:

    * Login to the google account with this app credentials   
    (you can find those credentials on file main.py line ~43) 
    
    * go to security settings -> allow less secure app

    * (More info -> https://support.google.com/accounts/answer/6010255?hl=en)

    If still not working:

    * after log in with the google account open this link:  
      https://accounts.google.com/DisplayUnlockCaptcha

    * (More info -> https://stackoverflow.com/questions/16512592/login-credentials-not-working-with-gmail-smtp)


------
## Run the application

* Open 2 terminals

  - 1st one : go to flask-server folder and run main
  ```
  cd src/flask-server
  python main.py  
  ```

  - 2nd one : go to react-app folder and run the start script
  ```
  cd src/react-app
  npm start
  ```

The app should start automatically in the default browser at this point..  
(However the url to type in the browser is the following: http://localhost:3000/)


-------
## Deploy and run on server

Follow this guide:
https://drive.google.com/file/d/1hta5qeYVr-2U9mcQdjT0-a_NacvhYUPC/view?usp=sharing


--------
## Credits:

- Thomas Neveux
- Julie Massari
- Gabriele Romano


# Install Annotation tool
------------

The document provides instructions for setting up the EKEEL Video Annotation project locally on your pc.

è stato testato per funzionare su Ubuntu 22 <-> 24. 
Non testato (e non funzionante) su windows ma solo su linux

## First Installation

### Prerequisites: ffmpeg

Open a Terminal and type:
```bash
sudo apt update && sudo apt upgrade
sudo apt install ffmpeg
sudo apt install tesseract-ocr
sudo apt install libtesseract-dev
```

-----
### Prerequisites: Anaconda  

<br>

Ensure Anaconda/Conda configured in terminal:

To install follow [this guide](../../prerequisites/conda.md) 

<br>

Download the repository:
```bash 
git clone https://github.com/Teldh/ekeel.git
```

"cd" to the folder EKEELVideoAnnotation

    > cd {path to the folder EKEELVideoAnnotation}


conda create the python environment from a yml file
```
conda env create -f conda_environment.yml
conda activate ekeel_anno_env
```

(Facoltative) If you have a gpu, to improve performances:
```bash
conda install m2w64-toolchain
conda install libpython
```

Installation completed, with the environment activated launch the project with:
```bash
python main.py
```

<br>

-----
## On any Change in Environment Packages 

To avoid inconsistency between local and server, yml file has been used to enforce same environment state

open a terminal:

    > cd {inside folder EKEELVideoAnnotation}


overwrite the conda_environment.yml inside using
```
conda env export --no-builds | grep -v "^prefix: " | grep -v "en-core-web-lg" | grep -v "it-core-news-lg" > conda_environment.yml
```
and push the modifications to the repo. (The spacy models end up in the final distribution but must be ignored otherwise cause errors)

Then to synchronize the packages change in the server pull updates from the repo and on the server terminal update dependencies on the server:

The guide is [here](deploy.md#update-and-setup-video-annotation-app)



------
## Run locally

Start by running Anaconda/Conda terminal:

<br>

Activate the "myenv" virtual environment:

    > conda activate ekeel_anno_env

(Facoltative) Open VSCode with conda (if dev using VScode ide)

    > code

With the environment activated launch the app locally with:

    > python main.py


------
## Notes
    
- Email 

    After some months the email sender could stop working and you can find errors on register or forgot password:

    * Login to the google account with this app credentials   
    (you can find those credentials on file .env) 
    
    * go to security settings -> allow less secure app

    * (More info -> https://support.google.com/accounts/answer/6010255?hl=en)

    If still not working:

    * after log in with the google account open this link:  
      https://accounts.google.com/DisplayUnlockCaptcha

    * (More info -> https://stackoverflow.com/questions/16512592/login-credentials-not-working-with-gmail-smtp)
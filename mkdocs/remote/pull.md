# Pulling updates from the github repo
----------

## Connect to the Server
```bash
ssh torre@130.251.47.107
# passw: < ask to project administrator >
```

-----
## Update Ekeel App Files from the Repository

Go inside app folder (/var/www/ekeel)
```bash
cd /var/www/ekeel
# Pull new versions of files from repository
sudo git pull
# username for github: Mirwe
# password: < ask to project administrator >
```
*Note: If github credentials are not valid or you want to use your own credentials...*


### Bug: Provided github credentials are not valid
You can use your own github credentials:
```bash
$ git clone https://github.com/...
Username: your_username
Password: your_token # (how to create a personal github access token)
```
A guide on how to do it is [here](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)

-----
## In case of Reinstall

Go in static folder, then create folder videos and give permissions

```bash
cd /var/www/ekeel/EVA_apps/EKEELVideoAnnotation/static
# create the folder if you don't have it already
sudo mkdir videos
sudo chmod 777 ./videos
```

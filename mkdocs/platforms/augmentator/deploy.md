# Deploy Augmentator on Server
------


## Update and Setup Video Augmentation App
Go inside EkeelVideoAugmentation app folder
```bash
cd /var/www/ekeel/EVA_apps/EkeelVideoAugmentation/
```

Go inside flask-server folder and update dependencies from requirements.txt
```bash
cd ./src/flask-server/
conda env update --file conda_environment.yml --prune
sudo systemctl restart ekeel-aug
```

Go inside react-app folder
```bash
cd /var/www/ekeel/EVA_apps/EkeelVideoAugmentation/src/react-app
```

If you have a build folder, delete it
```bash
sudo rm -r ./build
```

Update npm packages
```bash
sudo npm install --legacy-peer-deps
```

Create new version of the react app build
```bash
sudo -s
npm run build
```

Restart VideoAugmentation App
```bash
sudo systemctl restart ekeel-wp3
```

## In case of reinstall on server
After cloning the repo install nvm
```
sudo apt-get update
sudo apt install curl
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.1/install.sh | bash
```
Check the installation
```
nvm --version
```

Follow [this guide](install.md#front-end-reactjs) to install react front-end (specific section)
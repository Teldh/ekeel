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
sudo /home/anaconda3/envs/env-wp3/bin/pip install -r ./requirements.txt
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
Clone the repo
```
git clone https://github.com/
```

Follow [this guide](install.md) to install flask backend and react frontend
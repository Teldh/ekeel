# Deploy Ekeel App on Server
----------


## Update and Setup Video Annotation App
Go inside EKEELVideoAnnotation app folder
```bash
cd /var/www/ekeel/EVA_apps/EKEELVideoAnnotation/
```

Update prune (TODO not always works, sometimes happen that one has to delete environment and reinstall due to conflicts) and restart
```bash
conda env update --file conda_environment.yml --prune
sudo systemctl restart ekeel
```

-----
## Launch gunicorn
*(done automatically by "systemctl ekeel", use only for debugging)*

For infos about linux services used in this project look [here](../../prerequisites/linux-services.md)

```bash
cd /var/www/ekeel/EVA_apps/EkeelVideoAnnotation/
/home/anaconda3/envs/myenv/bin/gunicorn --bind 127.0.0.1:5050 connector:app --timeout 180 --limit-request-line 0
```

### View gunicorn instances
```bash
ps -ef|grep gunicorn
```

-----
## Run manually Video Augmentation App
*(done automatically by "systemctl ekeel", use only for debugging)*
```bash
cd /var/www/ekeel/EVA_apps/EkeelVideoAugmentation/src/flask-server
sudo /home/anaconda3/envs/env-wp3/bin/python ./main.py
```

-----
## Important Files
- **Github Repository folder:** `/var/www/ekeel`
- **Video Annotation folder:** `/var/www/ekeel/EVA_apps/EkeelVideoAnnotation/`
- **Video Augmentation folder:** `/var/www/ekeel/EVA_apps/EkeelVideoAugmentation/`
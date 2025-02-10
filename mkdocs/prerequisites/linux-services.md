# Prerequisites
------

## Commands for systemctl
*These commands should be used for debugging or for big changes in the server structure.*

*3 important modules of systemctl (use as `<name>` in commands):*

- `ekeel` (Video Annotation App)

- `ekeel-wp3` (Video Augmentation App)

- `nginx` (Global connection for the server)

### NGinx
------
NGINX is used as a reverse proxy to route incoming HTTP requests to the appropriate backend services. It ensures that the Video Annotation and Video Augmentation services are accessible through a single domain and handles load balancing and static file serving.

- Video Annotation Service: `/etc/systemd/system/ekeel.service`
- Video Augmentation Service: `/etc/systemd/system/ekeel-wp3.service`

#### Configuration
- Main config file: `/etc/nginx/sites-enabled/ekeel`

#### URL Routing
- `/` - React frontend for video augmentation
- `/api` - Backend API for video augmentation
- `/annotator/*` - Video annotation tool routes 
  - Uses reverseProxy configuration from config.py

## Service Management
The following commands manage nginx (should be used only for debugging or when edit any ```.service``` files )

```bash
# Reload systemd after config changes
sudo systemctl daemon-reload

# Restart NGINX
sudo systemctl restart nginx
```


The following commands manage Ekeel systemd services, which handle tasks like starting automatically on boot, logging system outputs, and ensuring minimal downtime.

```bash
# Enable systemctl service
sudo systemctl enable <name>

# View info about status
sudo systemctl status <name>

# Start the app
sudo systemctl start <name>

# Stop the app
sudo systemctl stop <name>

# Check app logs
sudo journalctl -u <name>
```

-------
## Open router ports

Port 5000 must be opened to allow external access to the Flask server:

1. Router Configuration
   - Log into your router's admin interface
   - Navigate to Port Forwarding/NAT settings
   - Add a new port forwarding rule:
     - External Port: 5000
     - Internal Port: 5000
     - Protocol: TCP
     - Internal IP: Your server's local IP address

2. Firewall Configuration

( #TODO check this, I did not handle this step, this is a placeholder for some commands on opening a router port )

```bash
sudo ufw status | grep 5000
sudo ufw allow 5000/tcp
sudo netstat -tuln | grep 5000
```
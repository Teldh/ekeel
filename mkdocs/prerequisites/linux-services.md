# Prerequisites
------

## Commands for systemctl
*These commands should be used for debugging or for big changes in the server structure.*

*3 important modules of systemctl (use as `<name>` in commands):*
- `ekeel` (Video Annotation App)
- `ekeel-wp3` (Video Augmentation App)
- `nginx` (Global connection for the server)

```bash
# Enable systemctl
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

```bash
sudo ufw status | grep 5000
sudo ufw allow 5000/tcp
sudo netstat -tuln | grep 5000
```
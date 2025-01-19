# Prerequisites
-----

## Mandatory files
You must put a `secrets.env` file when installed locally and must be moved inside folder under `\EVA_apps\sharedSecrets`, ask the project manager to access the file

------
## Miniconda Installation Guide for Linux
------

### Download Miniconda Installer
```bash
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
```

### Run the Installer
```bash
bash Miniconda3-latest-Linux-x86_64.sh
```

### Installation Prompts
1. Press `Enter` to view license
2. Type `yes` to accept the license
3. Press `Enter` to confirm installation location
4. Type `yes` to initialize Miniconda3

### Activate Installation
```bash
source ~/.bashrc
```

### Verify Installation
```bash
conda --version
```

### Clean Up Installer
```bash
rm Miniconda3-latest-Linux-x86_64.sh
```

**Note:** Restart your terminal or run `source ~/.bashrc` after installation.
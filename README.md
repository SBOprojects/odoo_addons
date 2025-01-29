# Managing Odoo Service on Hetzner Linux Console

This guide provides instructions for managing the Odoo service hosted on a Hetzner Linux server. It covers essential commands, configuration file locations, and logs.

## Table of Contents
1. [Service Management](#service-management)
2. [Configuration Files](#configuration-files)
3. [Log Files](#log-files)
4. [Backup and Restore](#backup-and-restore)
5. [Tips and Troubleshooting](#tips-and-troubleshooting)

---

## 1. Service Management

Use the following commands to manage the Odoo service on the Linux console.

### Start the Odoo Service
sudo systemctl start odoo18.service
Stop the Odoo Service


sudo systemctl stop odoo18.service
Restart the Odoo Service

sudo systemctl restart odoo18.service
Check the Odoo Service Status

sudo systemctl status odoo18.service

## 2. Configuration Files
Odoo Configuration File
The primary configuration file for Odoo is:


/etc/odoo/odoo.conf
Key Parameters in odoo.conf:
Database Host: db_host
Database Port: db_port
Database Name: db_name
Log File Path: logfile
Addons Path: addons_path
Edit the file with a text editor:


sudo nano /etc/odoo/odoo.conf
Odoo Custom Addons Directory
Custom modules are usually stored in:

/opt/odoo/addons/
Ensure the directory path is included in the addons_path parameter of odoo.conf.

## 3. Log Files
Odoo Logs
Odoo logs are crucial for troubleshooting and debugging. The default log file is located at:


/var/log/odoo/odoo.log
View Logs in Real-Time

sudo tail -f /var/log/odoo/odoo.log
## 4. Backup and Restore
Backup the Odoo Database
Use the following command to back up your Odoo database:


sudo pg_dump -U <db_user> -h <db_host> <db_name> > /path/to/backup.sql
Replace <db_user>, <db_host>, and <db_name> with your database credentials.

Restore the Odoo Database

sudo psql -U <db_user> -h <db_host> <db_name> < /path/to/backup.sql
## 5. Tips and Troubleshooting
Check Disk Space
Ensure there is sufficient disk space for logs, database backups, and other files:


df -h
Reload the Odoo Service After Changes
If you modify the odoo.conf file or update modules, reload the Odoo service:


View All Active Connections
To check database connections:

sudo netstat -tunlp | grep <db_port>


## 6. GitHub Commands
Basic Commands
Clone a Repository:


git clone <repository_url>
Check Current Status:


git status
Add Files to Staging:


git add <file_name>  # Add specific file
git add .            # Add all changes
Commit Changes:


git commit -m "Your commit message"
Push Changes:


git push origin <branch_name>
Overwriting Changes
Force Push Changes (Overwrite Remote):

bash
Copy
Edit
git push origin <branch_name> --force
Discard Local Changes:


git reset --hard
git clean -fd
Pull and Overwrite Local Changes:


git fetch origin
git reset --hard origin/<branch_name>
Fetching and Merging
Fetch Updates Without Merging:

git fetch origin
Merge Updates:


git merge origin/<branch_name>
Pull Updates (Fetch + Merge):


git pull origin <branch_name>
Branch Management
Check All Branches:


git branch -a
Switch Branch:


git checkout <branch_name>
Create a New Branch:


git checkout -b <new_branch_name>
Delete a Local Branch:


git branch -d <branch_name>
Delete a Remote Branch:


git push origin --delete <branch_name>


to overwrite a specific file use 
sudo wget -O <filename> <raw file link>

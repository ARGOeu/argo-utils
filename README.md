# argo-utils

Python Scripts for Maintainance and Administration of ARGO Components

MongoDB Incremental BackUp
----------------
MongoDB Incremental BackUp is a script that performs dumps of the mongodb oplog collection.

Requirements
------------

- pymongo

How to run MongoDB Incremental BackUp
--------------------------

`./mongodb_incremental_backup.py --host localhost --port 27017 --dir /var/lib/mongodb_data
 --logfile /var/log/incr_backup.log --gzip`

- `--host` is the mongodb host to connect to.
- `--port` is the mongodb port to connect to.
- `--dir` is the directory that will be used to save the backup and look for previous backup's timestamp.
- `--logfile` is the file where logs are going to be hold.
- `--gzip` is there to control whether or not to compress the back up files.
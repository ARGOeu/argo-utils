#!/bin/bash

#########################################################################################
# MySQL Backup - A simple script that compresses all the necessary files needed for
# a complete backup.
#
# Copyright (C) 2020 GRNET.
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# Along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.   
#
# Contributor(s):
#	* Anastasios Lisgaras <tasos@admin.grnet.gr>
#########################################################################################

#set -u
set -f
set -o pipefail

while getopts h:u:p:d:f: option 
do
	case "${option}" in
	h|--help)
		echo -e "MySQL Backup."
		echo -e "------------------------------------------------------------------------------------------ "
		echo -e "mysqlBackup.sh [arguments]"
		echo -e " "
		echo -e "Arguments:"
		echo -e "--help \tShow brief help."
		echo -e "-u \tDatabase username - Specify the username that has rights in the database you want to back up."
		echo -e "-p \tDatabase password - Specify the database user password."
		echo -e "-d \tDatabase name\t  - Specify the name of the database for which you want to back up."
		echo -e "-f \tDirectories or files\t  - Specify the name of the directories or files for which you want to back up."
		echo -e "\tNote: If you want, you can also archive multiple directories or files by separating the paths of the files or directories with ':'."
		echo -e "------------------------------------------------------------------------------------------ "
		echo -e "Usage: ./mysqlBackup.sh -u user -p 'password' -d database -f file:directory"
		exit 0
		;;
	u) DATABASE_USER=${OPTARG} ;;
	p) DATABASE_PASSWORD=${OPTARG} ;;
	d) DATABASE_NAME=${OPTARG} ;;
	f) FOR_ARCHIVING=${OPTARG} ;;
	esac
done

# Arguments validation.
if [[ -z "$DATABASE_NAME" ]]; then
	echo >&2 "The database name (-d) is required!"
    exit 1
fi

if [[ -z "$DATABASE_USER" ]]; then
	echo >&2 "The database user (-u) is required!"
    exit 1
fi

if [[ -z "$DATABASE_PASSWORD" ]]; then
	echo >&2 "The database password (-p) is required!"
    exit 1
fi

timestamp=$(date +%Y-%m-%d)
database_dumps="/var/backups/database"
archives="/var/backups/archives"
FOR_ARCHIVING=$(echo $FOR_ARCHIVING | sed 's/:/ /g' )


## Create directories if doesn't exist.
[ ! -d $database_dumps	] && mkdir -p ${database_dumps}
[ ! -d $archives		] && mkdir -p ${archives}


# Backup files 
## SQL.
mysqldumb="/usr/bin/mysqldump --user='$DATABASE_USER'  --password='$DATABASE_PASSWORD'  --lock-tables --databases ${DATABASE_NAME} > ${database_dumps}/${timestamp}_${HOSTNAME}_${DATABASE_NAME}.sql"
eval "$mysqldumb"


## Archive the hashing file of gocdb files, web server configuration files, web server logs and database.
cd ${database_dumps} && \
tar -zcpvf ${archives}/${timestamp}_${HOSTNAME}.tar.gz \
	${timestamp}_${HOSTNAME}_${DATABASE_NAME}.sql \
	${FOR_ARCHIVING} 


# We want to evaluate whether it was executed successfully or not.
tar_status=$?

# Delete unnecessary files
rm -rf ${database_dumps}
find ${archives} -type f -mtime +60 -exec rm {} \;


# Logs
if [[ ${tar_status} -eq 0 ]]; then
    logger "[mySQLBackupScript]: Executed successfully"
	exit 0;
else
    logger "[mySQLBackupScript]: Failed to execute" level=error
	exit 1;
fi




# vim: syntax=sh ts=4 sw=4 sts=4 sr noet

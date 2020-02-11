#!/usr/bin/env python

import os
import pymongo
import datetime
import subprocess
import bson
import logging
import argparse
import sys

# set up logging
LOGGER = logging.getLogger("MongoDB Incremental BackUp Script")


def last_recorded_timestamp(dir_name):
    """Retrieve the latest recorded timestamp corresponding to the latest incremental backup.
       Args:
           dir_name: str. Directory where the last recorded backup should be found.
       Return:
           bson.timestamp.Timestamp
    """

    # check if the provided directory exists, otherwise create it
    if not os.path.exists(dir_name):
        LOGGER.info("Directory %s doesn't exist. Creating it ...", dir_name)
        os.mkdir(dir_name)
        # since the directory was not even present, there is no starting timestamp present
        return None

    # find the latest backup directory and use its timestamp
    latest_entry = None

    LOGGER.info("Scanning directory %s ...", dir_name)
    with os.scandir(dir_name) as it:
        for entry in it:
            if latest_entry is not None:
                if latest_entry.stat().st_ctime_ns < entry.stat().st_ctime_ns:
                    latest_entry = entry
            else:
                latest_entry = entry

    LOGGER.info("Directory with the latest backup %s", os.path.join(dir_name,latest_entry.name))

    # check if there is a timestamp file present(it should always be present)
    if os.path.exists(os.path.join(dir_name,latest_entry.name, "local", "timestamp")):
        with open(os.path.join(dir_name,latest_entry.name, "local", "timestamp")) as f:
            read_data = f.read()

        LOGGER.info("Last recorded timestamp %s", read_data)
        # the contents of the timestamp file should be in the form of Timestamp(1581417721, 1)

        _ts = read_data[10:].strip(")").split(",")

        return bson.timestamp.Timestamp(time=int(_ts[0]), inc=int(_ts[1]))
    else:
        LOGGER.critical("Directory %s doesn't contain a timestamp file", os.path.join(dir_name,latest_entry.name,"local"))
        return None


def mongo_last_available_timestamp(host, port):
    """Retrieve the latest available timestamp from MongoDB.
       Args:
           host: str. MongoDB host.
           port: int. MongoDB port.
       Return:
           bson.timestamp.Timestamp
    """
    LOGGER.info("Opening Connection to MongoDB(%s,%s)...", host, port)
    client = pymongo.MongoClient(host, port)
    oplog = client.local.oplog.rs
    first = oplog.find().sort('$natural', pymongo.DESCENDING).limit(1).next()
    ts = first['ts']
    return ts

def generate_export_command(mongo_host, mongo_port, starting_timestamp, end_timestamp, date, dir_out, gzip=False):
    """Formulate the mongodump command.
       Args:
           mongo_host: str. MongoDB host.
           mongo_port: int. MongoDB port.
           starting_timestamp: bson.timestamp.Timestamp. Timestamp to used for the mongodump query as a lower bound.
           end_timestamp: bson.timestamp.Timestamp. Timestamp to used for the mongodump query as an upper bound.
           date: str. Current date to be used in save path.
           dir_out. str. Directory to be used in save path.
           gzip. bool. Whether or not to include the gzip option in the mongodump.
       Return:
           list
    """

    if starting_timestamp is not None:

        query = """{{ "ts": {{ "lte": {{ "$timestamp": {{"t":{0}, "i":{1} }}}}}}, "ts": {{ "$gte": {{ "$timestamp": {{"t":{2}, "i":{3} }}}}}}}}"""\
            .format(
            end_timestamp.time,
            end_timestamp.inc,
            starting_timestamp.time,
            starting_timestamp.inc

        )

    else:
        query = """{{ "ts": {{ "$lte": {{ "$timestamp": {{ "t": {0}, "i": {1} }}}}}}}}""".format(
            end_timestamp.time,
            end_timestamp.inc
        )

    # start building the mongodump command

    mongodump_cmd = list()

    # add the mongodump script
    mongodump_cmd.append("mongodump")

    # add host and port for the mongodb connection
    mongodump_cmd.append("--host")
    mongodump_cmd.append('{0}:{1}'.format(mongo_host, mongo_port))

    # add mongodb collection
    mongodump_cmd.append("--db")
    mongodump_cmd.append("local")

    # add the oplog collection
    mongodump_cmd.append("--collection")
    mongodump_cmd.append("oplog.rs")

    # add the save path for the dump
    mongodump_cmd.append("--out")
    mongodump_cmd.append(os.path.join(dir_out, date))

    # add the export query
    mongodump_cmd.append("--query")
    mongodump_cmd.append(query)

    # add the gzip option
    if gzip:
        mongodump_cmd.append("--gzip")

    return mongodump_cmd


def main(args):

    # stream(console) handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(name)s[%(process)d]: %(levelname)s %(message)s'))
    LOGGER.addHandler(console_handler)
    LOGGER.setLevel(logging.INFO)

    if args.logfile is not None:
        file_handler = logging.FileHandler(args.logfile)
        file_handler.setFormatter(logging.Formatter('%(name)s[%(process)d]: %(levelname)s %(message)s'))
        LOGGER.addHandler(file_handler)

    date = datetime.datetime.now().strftime('%A_%Y-%m-%dT%H:%M:%SZ')
    try:
        starting_timestamp = last_recorded_timestamp(args.dir)

        end_timestamp = mongo_last_available_timestamp(args.host, args.port)

        mongodump_cmd = generate_export_command(args.host, args.port, starting_timestamp, end_timestamp, date, args.dir, args.gzip)

        LOGGER.info("Executing command %s", " ".join(mongodump_cmd))

        rc = subprocess.check_call(mongodump_cmd)
        if rc==0:
            f = open(os.path.join(args.dir, date, "local", "timestamp"), "w+")
            f.write(str(end_timestamp))
            f.close()
    except Exception as e:
        LOGGER.critical("Could not backup, {}".format(str(e)))

    LOGGER.info("Latest BackUp at %s", os.path.join(args.dir, date,))


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Perform incremental backup for a MongoDB utilizing the oplog")

    parser.add_argument(
        "-host", "--host", metavar="STRING", help="MongoDB Host",  default="localhost", type=str, dest="host", required=True)

    parser.add_argument(
        "-port", "--port", metavar="INTEGER", help="MongoDB Port", default=27017, type=int, dest="port")

    parser.add_argument(
        "-dir", "--dir", metavar="STRING", help="Output directory", type=str, dest="dir", required=True)

    parser.add_argument(
        "-gzip", "--gzip", help="Compression for the created backup", dest="gzip", action="store_true")

    parser.add_argument(
        "-logfile", "--logfile", metavar="STRING", help="Log file", type=str, dest="logfile")

    sys.exit(main(parser.parse_args()))
#!/bin/bash
chown -R mongodb:mongodb /data/db
chown mongodb:mongodb /etc/mongocfg/mongodb-keyfile
chmod 400 /etc/mongocfg/mongodb-keyfile
exec "$@"

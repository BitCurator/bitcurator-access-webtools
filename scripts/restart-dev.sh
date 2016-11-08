#!/usr/bin/env bash

service nginx stop
service uwsgi stop

## vagrant ssh --command /vagrant/restart-dev.sh
WWW_ROOT=/var/www
BCAW_ROOT="$WWW_ROOT/bcaw"
BCAW_TARGET="$BCAW_ROOT/bcaw"
SOURCE_ROOT="/vagrant"
BCAW_SOURCE="$SOURCE_ROOT/bcaw"

if [ -d "$BCAW_TARGET" ]; then
  find "$BCAW_TARGET" -name "*.pyc" -type f -exec rm {} \;
fi

if [ -d "$BCAW_TARGET" ]; then
  rm "$BCAW_ROOT/"*.py
  find "$BCAW_TARGET" -name "*.py" -type f -exec rm {} \;
fi

cp -f "$SOURCE_ROOT/"*.py "$BCAW_ROOT"
cp -fr "$BCAW_SOURCE" "$BCAW_ROOT"
chown www-data:www-data "$BCAW_ROOT/"*.py
chown -R www-data:www-data "$BCAW_TARGET"
sudo rm /var/log/bcaw.log
sudo touch /var/log/bcaw.log
sudo chmod 666 /var/log/bcaw.log

service nginx start
service uwsgi start

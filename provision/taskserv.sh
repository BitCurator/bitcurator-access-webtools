#!/usr/bin/env bash

SCRIPT_PATH=$(dirname $(readlink -f $0 ) )

##
# Bash script to provision VM, used to set up BCA environment.
#
##

# celery -A bcaw_celery_task.celery worker --loglevel=INFO &

cd /vagrant
sudo cp provision/celeryd /etc/default/celeryd
sudo /etc/init.d/celeryd start



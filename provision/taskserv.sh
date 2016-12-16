#!/usr/bin/env bash
#
# Provision VM for bitcurator-access-webtools
#

SCRIPT_PATH=$(dirname $(readlink -f $0 ) )

#cd /vagrant
#su www-data -c "celery -A bcaw_celery_task.celery worker --concurrency=1 --loglevel=INFO &"
cd /var/www/bcaw
su vagrant -c "/var/www/bcaw/venv/bin/celery -A bcaw_celery_task.celery worker --concurrency=1 --loglevel=INFO &>> /tmp/celery.log &"

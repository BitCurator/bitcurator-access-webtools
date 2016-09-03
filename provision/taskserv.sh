#!/usr/bin/env bash

SCRIPT_PATH=$(dirname $(readlink -f $0 ) )

##
# Bash script to provision VM, used to set up BCA environment.
#
##

# celery -A bcaw_celery_task.celery worker --loglevel=INFO &

# celeryd has been deprecated. Use celery worker command instead
# cd /vagrant
# sudo cp provision/celeryd /etc/default/celeryd
# sudo /etc/init.d/celeryd start

#cd /vagrant
#su www-data -c "celery -A bcaw_celery_task.celery worker --concurrency=1 --loglevel=INFO &"

cd /var/www/bcaw
su vagrant -c "/var/www/bcaw/venv/bin/celery -A bcaw_celery_task.celery worker --concurrency=1 --loglevel=INFO &"

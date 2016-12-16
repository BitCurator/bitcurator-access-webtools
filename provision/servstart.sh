#!/usr/bin/env bash
#
# Provision the VM for bitcurator-access-webtools
#
# This script is *only* run the first time you issue the
#
#    vagrant up
#
# command, or following a
#
#    vagrant destroy
#    vagrant up
#
# combination.  See README.md for further detais.
#

SCRIPT_PATH=$(dirname $(readlink -f $0 ) )


# Start the Flask server / app
cd /var/www/bcaw
python runbcaw.py &



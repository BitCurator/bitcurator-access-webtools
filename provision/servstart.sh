#!/usr/bin/env bash

SCRIPT_PATH=$(dirname $(readlink -f $0 ) )

##
# Bash script to provision VM, used to set up BCA environment.
#
# Be aware this script is only the first time you issue the
#    vagrant up
# command, or following a
#    vagrant destroy
#    vagrant up
# combination.  See the README for further detais.
##

#start the server
cd /vagrant
python runserver.py &

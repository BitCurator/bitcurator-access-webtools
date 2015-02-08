#!/usr/bin/python
# coding=UTF-8
#
# BitCurator Access Webtools (Disk Image Access for the Web)
# Copyright (C) 2014
# All rights reserved.
#
# This code is distributed under the terms of the GNU General Public
# License, Version 3. See the text file "COPYING" for further details
# about the terms of this license.
#
# This is a python __init__ script to create the app and import the
# main package contents

from flask import Flask
app = Flask(__name__)

# Config file:
# For the from_envvar to work, dimac_settings.cfg is to be populated 
# and the env variable BCAW_SETTINGS is to be set to this path:
# Ex: cat /home/bcadmin/myflask/dimac/dimac/settings.cfg
# IMAGEDIR = "/home/bcadmin/disk_images"
# export BCAW_SETTINGS=/home/bcadmin/myflask/dimac/dimac/settings.cfg
# It is commented out here. IT can be uncommented once the above
# export command is executed. The default setting can be changed in 
# the line below, as an alternative.

app.config['IMAGEDIR'] = "/vagrant/disk-images"
# app.config.from_envvar('BCAW_SETTINGS')

import bcaw.image_browse

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
import logging

# Configure logging across all modules
FORMAT="[%(levelname)-8s %(filename)-15s:%(lineno)-5d %(funcName)-30s] %(message)s"
logging.basicConfig(filename='/var/log/bcaw.log', level=logging.DEBUG, format=FORMAT)
logging.debug("Restarting Flask application.");
app = Flask(__name__)
# Config file:

# Adding the following line will allow the configurations to be
# defined in the specified file - bcaw_default_settings.py. Doing so
# will add the corresponding elements to the dectionary app.config
# and populate them with the given values.
logging.debug("Initialising default configuration.");
app.config.from_object('bcaw_default_settings')

# NOTE: From another site: http://code.tutsplus.com/tutorials/intro-to-flask-signing-in-and-out--net-29982
# FIXME: Config info in app.confic dictionary could be moved to the
# default config file.
app.secret_key = 'development key'

import bcaw_db as db
logging.debug("Initialising database.");
db.dbinit()

import bcaw.image_browse

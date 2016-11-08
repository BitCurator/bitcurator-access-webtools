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

# Load the application
from flask import Flask
app = Flask(__name__)
# Get the appropriate config
import config
config.configure_app(app)

# Configure logging across all modules
import logging
from const import *
logging.basicConfig(filename=app.config[ConfKey.LOG_FILE], level=logging.DEBUG, format=app.config[ConfKey.LOG_FORMAT])
logging.info("Started BCAW Flask app.");
logging.debug("Configured logging.");

# Initialise the database
import model
logging.info("Initialising database connection.");
model.dbinit()

# Import the application routes
logging.info("Setting up application routes");
import controller
logging.info("Synching disk and db.")
if controller.DbSynch.is_synch_db():
    controller.DbSynch.synch_db()

#!/usr/bin/env python
# coding=UTF-8
#
# BitCurator Access Webtools (Disk Image Access for the Web)
# Copyright (C) 2014 - 2016
# All rights reserved.
#
# This code is distributed under the terms of the GNU General Public
# License, Version 3. See the text file "COPYING" for further details
# about the terms of this license.
#
"""
BitCurator Access web application.

Initialisation module for package, kicks of the flask app.

"""
__version__ = '0.1.0'
import logging
# Load the application
from flask import Flask
APP = Flask(__name__)

# Get the appropriate config
from .config import configure_app # pylint: disable-msg=C0413
configure_app(APP)
from .utilities import sizeof_fmt
APP.jinja_env.globals.update(sizeof_fmt=sizeof_fmt)

# Configure logging across all modules
logging.basicConfig(filename=APP.config['LOG_FILE'], level=logging.DEBUG,
                    format=APP.config['LOG_FORMAT'])
logging.info("Starting BitCurator Web Access tools server.")

from .model import init_db # pylint: disable-msg=C0413
logging.debug("Configured logging.")
logging.info("Initialising database.")
init_db()

logging.info("Setting up application routes")
from .controller import ROUTES # pylint: disable-msg=W0403, W0611, C0413, C0411

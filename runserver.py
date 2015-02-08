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
# This is a python script to run the main app server

from bcaw import app
#from bcaw import bcaw_db
#bcaw_db.bcawdb()

app.debug=True
app.run('0.0.0.0')


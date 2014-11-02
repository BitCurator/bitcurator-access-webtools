#!/usr/bin/python
# coding=UTF-8
#
# bca-webtools: Disk Image Access for the Web
# Copyright (C) 2014
# All rights reserved.
#
# This code is distributed under the terms of the GNU General Public
# License, Version 3. See the text file "COPYING" for further details
# about the terms of this license.
#
# This is a python script to run the main app server

from bca-webtools import app
#from dimac import dimac_db
#dimac_db.dimacdb()

app.run(debug=True)


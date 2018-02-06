#!/usr/bin/python
# coding=UTF-8
#
# BitCurator Access Webtools (Disk Image Access for the Web)
# Copyright (C) 2014 - 2018
# All rights reserved.
#
# This code is distributed under the terms of the GNU General Public
# License, Version 3. See the text file "COPYING" for further details
# about the terms of this license.
#
# This file contains celery support code for the BitCurator Access Webtools application.
#

from flask import Flask, current_app
from bcaw import app
from celery import Celery
import bcaw
from bcaw import *

# Originally defined in bcaw_default_settings.py. May need to be moved.
app.config['CELERY_BROKER_URL'] = 'amqp://guest@localhost//'
app.config['CELERY_RESULT_BACKEND'] = 'amqp://guest@localhost//'

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

@celery.task(bind=True)
def bcawIndexAsynchronously(self):
    """ The Celery worker task. Run in parallel with the bcaw app. When Lucene 
        indexes for disk images are generated, the main app (bcaw) calls this 
        worker thread which in turn, invokes the indexing routine.
        Invoked by the following command:
        $ celery -A bcaw_celery_task.celery  worker --loglevel=INFO
    """

    """ Background task to index the files """
    # print "[D]: Task_id: ", self.request.id
    with app.app_context():
        # print "Calling bcawIndexAllFiles..."
        # print "Current app: ", current_app.name
        bcaw.image_browse.bcawIndexAllFiles(self.request.id)

@celery.task(bind=True)
def bcawBuildDfxmlTableAsynchronously(self):
    """ Background task to build dfxml table """
    with app.app_context():
        # print "Calling dbBuildDb for DFXML..."
        # print "Current app: ", current_app.name
        bcaw.bcaw_db.dbBuildDb(self.request.id, bld_imgdb = False, bld_dfxmldb = True)

@celery.task(bind=True)
def bcawBuildAllTablesAsynchronously(self):
    """ Background task to build image and dfxml table """
    with app.app_context():
        # print "Calling dbBuildDb for DFXML..."
        # print "Current app: ", current_app.name
        bcaw.bcaw_db.dbBuildDb(self.request.id, bld_imgdb = True, bld_dfxmldb = True)

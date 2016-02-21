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
# This file contains celery support code for the BitCurator Access Webtools application.
#

from flask import Flask, current_app
from bcaw import app
from celery import Celery
import bcaw
from bcaw import *

# FIXME: The following are already defined in bcaw_default_Settings.py.
# Need to figure out how to include that file here so the following 2 lines
# can be removed.
app.config['CELERY_BROKER_URL'] = 'amqp://guest@localhost//'
app.config['CELERY_RESULT_BACKEND'] = 'amqp://guest@localhost//'

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

@celery.task(bind=True)
#def bcawIndexAsynchronously(bind=True):
def bcawIndexAsynchronously(self):
    """ This is the Celery worker task which is run in parallel with the
        bcaw app. When user chooses to generate Lucene indexes for the disk
        images, the mail app (bcaw) calls this worker thread which in turn,
        invokes the indexing routine.
        This task is invoked by the following command:
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

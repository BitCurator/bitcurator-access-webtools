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
# This file contains the main BitCurator Access Webtools application.
#

from bcaw import app
#from bcaw_utils import all
#from bcaw import app
#from image_browse import all
from celery import Celery
#from bcaw import image_browse
#from bcaw import image_browse
import bcaw

app.config['CELERY_BROKER_URL'] = 'amqp://guest@localhost//'
app.config['CELERY_RESULT_BACKEND'] = 'amqp://guest@localhost//'

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

@celery.task
def bcaw_index_asynchronously():
    """ Background task to index the files """
    print "III: in async_indexing func "
    with app.app_context():
        print "Calling bcawIndexAllFiles..."
        bcaw.image_browse.bcawIndexAllFiles()


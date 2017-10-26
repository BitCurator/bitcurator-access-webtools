#!/usr/bin/python
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
# This file contains items that can be configured in BitCurator Access Webtools.
#
"""Module for application config goodness."""
import os
# TODO: template these values for flexible install
HOST = 'localhost'
DB_HOST = 'localhost'
ROOT = '/var/www/bcaw/'
LOG_ROOT = '/var/log/'
DB_USER = 'vagrant'
DB_PASS = 'vagrant'
DB_NAME = 'bca_db'
POSTGRES_URI = 'postgresql://' + DB_USER + ':' + DB_PASS + '@' + DB_HOST + '/' + DB_NAME
LUCENE_ROOT = '/var/www/.index'
GROUPS = '[{"name": "Test Images", ' \
              '"path": "/var/www/bcaw/disk-images", ' \
              '"description": "The set of test disk images supplied with BitCurator"}]'
class BaseConfig(object):
    """The basic default configuration."""
    HOST = HOST
    SQLALCHEMY_DATABASE_URI = POSTGRES_URI
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = True
    LOG_FORMAT = '[%(filename)-15s:%(lineno)-5d] %(message)s'
    LOG_FILE = LOG_ROOT + 'bcaw.log'
    LUCENE_INDEX_DIR = LUCENE_ROOT

class DevConfig(BaseConfig):
    """Development config extras."""
    DEBUG = True
    LOG_FORMAT = '[%(levelname)-8s %(filename)-15s:%(lineno)-5d %(funcName)-30s] %(message)s'

CONFIGS = {
    "dev": 'bcaw.config.DevConfig',
    "default": 'bcaw.config.BaseConfig'
}

def configure_app(app):
    """Configure the application using the config env var."""
    config_name = os.getenv('BCAW_CONFIG', 'dev')
    app.config.from_object(CONFIGS[config_name])
